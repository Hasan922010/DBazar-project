/**
 * DBazar Offline-First Cloud POS Client (`apps/pos-client`)
 * Real SQLite Engine (`node:sqlite` DatabaseSync) with append-only `pos_stock_events` + HLC timestamps.
 */
import crypto from "node:crypto";
import { DatabaseSync } from "node:sqlite";
import {
  assertZeroJargonInText,
  designTokens,
  uzDictionary,
} from "../../../packages/ui-tokens/src/index.js";
import {
  formatTiyinUzs,
  generateHlcTimestamp,
  isValidMxikCode,
} from "../../../packages/shared-utils/src/index.js";
import { printEscPosReceipt } from "../../../packages/mocks-and-emulators/pos-hardware-sim/src/index.js";

export class OfflinePosDatabase {
  constructor(options) {
    this.storeId = options.storeId;
    this.terminalId = options.terminalId;
    this.storeName = options.storeName;
    this.isOnline = true;
    this.lastHlc = null;
    this.db = new DatabaseSync(options.dbPath || ":memory:");
    this.initSchema();
  }

  initSchema() {
    this.db.exec(`
      CREATE TABLE IF NOT EXISTS pos_catalog_items (
        variant_id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        mxik_code TEXT NOT NULL,
        barcode TEXT NOT NULL,
        batch_id TEXT NOT NULL,
        unit_price_tiyin INTEGER NOT NULL CHECK (unit_price_tiyin > 0)
      );

      CREATE TABLE IF NOT EXISTS pos_stock_events (
        client_event_id TEXT PRIMARY KEY,
        variant_id TEXT NOT NULL,
        batch_id TEXT NOT NULL,
        event_type TEXT NOT NULL CHECK (event_type IN ('INBOUND', 'SALE', 'RETURN', 'WRITE_OFF')),
        qty_delta INTEGER NOT NULL CHECK (qty_delta != 0),
        unit_price_tiyin INTEGER NOT NULL CHECK (unit_price_tiyin >= 0),
        hlc_timestamp TEXT NOT NULL,
        waybill_qr_token TEXT NOT NULL DEFAULT '',
        synced INTEGER NOT NULL DEFAULT 0
      );

      CREATE TABLE IF NOT EXISTS pos_sales (
        client_sale_id TEXT PRIMARY KEY,
        receipt_seq INTEGER NOT NULL,
        payment_method TEXT NOT NULL,
        customer_name TEXT NOT NULL DEFAULT '',
        total_amount_tiyin INTEGER NOT NULL CHECK (total_amount_tiyin > 0),
        hlc_timestamp TEXT NOT NULL
      );
    `);
  }

  nextHlc(nowMs = Date.now()) {
    this.lastHlc = generateHlcTimestamp(this.terminalId, this.lastHlc, nowMs);
    return this.lastHlc;
  }

  oneClickWaybillInbound(waybill, retailMarkupBps = 1500) {
    const upsertCatalog = this.db.prepare(`
      INSERT INTO pos_catalog_items (variant_id, name, mxik_code, barcode, batch_id, unit_price_tiyin)
      VALUES (?, ?, ?, ?, ?, ?)
      ON CONFLICT(variant_id) DO UPDATE SET
        name = excluded.name,
        mxik_code = excluded.mxik_code,
        barcode = excluded.barcode,
        batch_id = excluded.batch_id,
        unit_price_tiyin = excluded.unit_price_tiyin
    `);

    const checkEvent = this.db.prepare(
      `SELECT 1 FROM pos_stock_events WHERE client_event_id = ?`
    );

    const insertEvent = this.db.prepare(`
      INSERT INTO pos_stock_events (
        client_event_id, variant_id, batch_id, event_type, qty_delta, unit_price_tiyin, hlc_timestamp, waybill_qr_token, synced
      ) VALUES (?, ?, ?, 'INBOUND', ?, ?, ?, ?, 0)
    `);

    let inbounded = 0;
    this.db.exec("BEGIN IMMEDIATE");
    try {
      for (const item of waybill.items) {
        if (!isValidMxikCode(item.mxik_code)) {
          throw new Error(`Yuk xatida noto'g'ri 17 xonali MXIK: ${item.mxik_code}`);
        }
        const retailPriceTiyin =
          item.unit_price_tiyin + Math.trunc((item.unit_price_tiyin * retailMarkupBps) / 10000);

        upsertCatalog.run(
          item.variant_id,
          item.product_name,
          item.mxik_code,
          item.barcode,
          item.batch_id,
          retailPriceTiyin
        );

        const hash = crypto
          .createHash("sha256")
          .update(`pos-1click:${this.storeId}:${waybill.id}:${item.id}`)
          .digest("hex");
        const deterministicUuid = `${hash.slice(0, 8)}-${hash.slice(8, 12)}-5${hash.slice(13, 16)}-8${hash.slice(17, 20)}-${hash.slice(20, 32)}`;

        if (checkEvent.get(deterministicUuid)) {
          continue;
        }

        const hlc = this.nextHlc();
        insertEvent.run(
          deterministicUuid,
          item.variant_id,
          item.batch_id,
          item.quantity,
          item.unit_price_tiyin,
          hlc,
          waybill.waybill_qr_token
        );
        inbounded += 1;
      }
      this.db.exec("COMMIT");
    } catch (err) {
      this.db.exec("ROLLBACK");
      throw err;
    }

    return {
      waybillQrToken: waybill.waybill_qr_token,
      inboundedItemsCount: inbounded,
    };
  }

  getVariantStockQty(variantId) {
    const row = this.db
      .prepare(`SELECT COALESCE(SUM(qty_delta), 0) AS qty FROM pos_stock_events WHERE variant_id = ?`)
      .get(variantId);
    return Number(row?.qty ?? 0);
  }

  recordCheckoutEvent(options) {
    if (!Number.isInteger(options.quantity) || options.quantity <= 0) {
      throw new Error("Miqdor 0 dan katta butun son bo'lishi shart.");
    }
    const item = this.db
      .prepare(`SELECT * FROM pos_catalog_items WHERE variant_id = ?`)
      .get(options.variantId);
    if (!item) {
      throw new Error(`Tovar topilmadi: ${options.variantId}`);
    }

    const signedDelta =
      options.eventType === "RETURN" ? options.quantity : -options.quantity;
    const hlc = this.nextHlc(options.nowMs);
    const clientEventId = crypto.randomUUID();
    const lineTotalTiyin = item.unit_price_tiyin * options.quantity;

    this.db.exec("BEGIN IMMEDIATE");
    try {
      this.db
        .prepare(
          `INSERT INTO pos_stock_events (
            client_event_id, variant_id, batch_id, event_type, qty_delta, unit_price_tiyin, hlc_timestamp, waybill_qr_token, synced
          ) VALUES (?, ?, ?, ?, ?, ?, ?, '', 0)`
        )
        .run(
          clientEventId,
          item.variant_id,
          item.batch_id,
          options.eventType,
          signedDelta,
          item.unit_price_tiyin,
          hlc
        );

      if (options.eventType === "SALE") {
        const seqRow = this.db
          .prepare(`SELECT COALESCE(MAX(receipt_seq), 0) + 1 AS next_seq FROM pos_sales`)
          .get();
        this.db
          .prepare(
            `INSERT INTO pos_sales (client_sale_id, receipt_seq, payment_method, customer_name, total_amount_tiyin, hlc_timestamp)
             VALUES (?, ?, ?, ?, ?, ?)`
          )
          .run(
            crypto.randomUUID(),
            seqRow.next_seq,
            options.paymentMethod || "CASH",
            options.customerName || "",
            lineTotalTiyin,
            hlc
          );
      }
      this.db.exec("COMMIT");
    } catch (err) {
      this.db.exec("ROLLBACK");
      throw err;
    }

    const fiscalQrUrl = this.isOnline
      ? `https://ofd.soliq.uz/check?t=${this.terminalId}&hlc=${encodeURIComponent(hlc)}`
      : `offline-queue://ofd.soliq.uz/${this.terminalId}/${clientEventId}`;

    const receipt = printEscPosReceipt(
      this.storeName,
      [
        {
          name: item.name,
          mxikCode: item.mxik_code,
          qty: options.quantity,
          unitPriceTiyin: item.unit_price_tiyin,
          lineTotalTiyin,
        },
      ],
      lineTotalTiyin,
      fiscalQrUrl
    );

    return {
      clientEventId,
      hlcTimestamp: hlc,
      totalAmountTiyin: lineTotalTiyin,
      receipt,
    };
  }

  exportUnsyncedDeltaBatch() {
    const rows = this.db
      .prepare(
        `SELECT client_event_id, variant_id, batch_id, event_type, qty_delta, unit_price_tiyin, hlc_timestamp, waybill_qr_token
         FROM pos_stock_events
         WHERE synced = 0
         ORDER BY hlc_timestamp ASC`
      )
      .all();

    const events = rows.map((r) => ({
      client_event_id: r.client_event_id,
      variant_id: r.variant_id,
      batch_id: r.batch_id,
      event_type: r.event_type,
      quantity: Math.abs(r.qty_delta),
      unit_price_tiyin: r.unit_price_tiyin,
      hlc_timestamp: r.hlc_timestamp,
      waybill_qr_token: r.waybill_qr_token,
    }));

    return {
      store_id: this.storeId,
      events,
    };
  }

  markEventsSynced(clientEventIds) {
    const stmt = this.db.prepare(
      `UPDATE pos_stock_events SET synced = 1 WHERE client_event_id = ?`
    );
    this.db.exec("BEGIN IMMEDIATE");
    try {
      for (const id of clientEventIds) {
        stmt.run(id);
      }
      this.db.exec("COMMIT");
    } catch (err) {
      this.db.exec("ROLLBACK");
      throw err;
    }
  }
}

export function renderPosScreenHtml(pos, currentTotalTiyin) {
  const statusBanner = pos.isOnline
    ? `<div class="pos-status online"><span class="dot green"></span> Aloqa bor</div>`
    : `<div class="pos-status offline"><span class="dot yellow"></span> ${uzDictionary.offline.posOfflineBanner}</div>`;

  const html = `
    <div class="pos-split-layout">
      <header class="pos-topbar">
        <h1>${pos.storeName}</h1>
        ${statusBanner}
        <button type="button" class="btn-qr-inbound" style="min-height:${designTokens.spacing.minTouchTargetPosPx}px">
          Tovar qabul qilish (QR - F4)
        </button>
      </header>
      <div class="pos-columns">
        <section class="pos-left-catalog" aria-label="${uzDictionary.catalog.products}">
          <input type="search" placeholder="Shtrix-kod yoki tovar nomi (F2)" />
        </section>
        <section class="pos-right-receipt" aria-label="Chek">
          <div class="receipt-total tabular-nums">${formatTiyinUzs(currentTotalTiyin)}</div>
          <button type="button" class="btn-pos-pay" data-primary-cta="true" style="min-height:${designTokens.spacing.minTouchTargetPosPx}px">
            TO'LASH (F12)
          </button>
        </section>
      </div>
    </div>
  `;

  assertZeroJargonInText(html.replace(/<[^>]+>/g, " "));
  return html;
}
