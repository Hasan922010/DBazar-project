/**
 * DBazar Offline-First Cloud POS Client (`apps/pos-client`)
 * Real SQLite Engine (`node:sqlite` DatabaseSync) with append-only `pos_stock_events` + HLC timestamps.
 * Redesigned Keyboard-First 2-column POS workstation with 56px+ buttons and Soliq.uz Fiscal QR receipt.
 */
import crypto from "node:crypto";
import { DatabaseSync } from "node:sqlite";
import {
  assertZeroJargonInText,
  designTokens,
  uzDictionary,
} from "../../../packages/ui-tokens/src/index.js";
import {
  compareHlcTimestamps,
  escapeHtml,
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

    this.stmtGetCatalogItem = this.db.prepare(
      `SELECT * FROM pos_catalog_items WHERE variant_id = ?`
    );
    this.stmtGetStockQty = this.db.prepare(
      `SELECT COALESCE(SUM(qty_delta), 0) AS qty FROM pos_stock_events WHERE variant_id = ?`
    );
    this.stmtInsertCheckoutEvent = this.db.prepare(`
      INSERT INTO pos_stock_events (
        client_event_id, variant_id, batch_id, event_type, qty_delta, unit_price_tiyin, hlc_timestamp, waybill_qr_token, synced
      ) VALUES (?, ?, ?, ?, ?, ?, ?, '', 0)
    `);
    this.stmtNextReceiptSeq = this.db.prepare(
      `SELECT COALESCE(MAX(receipt_seq), 0) + 1 AS next_seq FROM pos_sales`
    );
    this.stmtInsertSale = this.db.prepare(`
      INSERT INTO pos_sales (client_sale_id, receipt_seq, payment_method, customer_name, total_amount_tiyin, hlc_timestamp)
      VALUES (?, ?, ?, ?, ?, ?)
    `);
    this.stmtMarkSynced = this.db.prepare(
      `UPDATE pos_stock_events SET synced = 1 WHERE client_event_id = ?`
    );
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
    const row = this.stmtGetStockQty.get(variantId);
    return Number(row?.qty ?? 0);
  }

  recordCheckoutEvent(options) {
    if (!Number.isInteger(options.quantity) || options.quantity <= 0) {
      throw new Error("Miqdor 0 dan katta butun son bo'lishi shart.");
    }
    const item = this.stmtGetCatalogItem.get(options.variantId);
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
      this.stmtInsertCheckoutEvent.run(
        clientEventId,
        item.variant_id,
        item.batch_id,
        options.eventType,
        signedDelta,
        item.unit_price_tiyin,
        hlc
      );

      if (options.eventType === "SALE") {
        const seqRow = this.stmtNextReceiptSeq.get();
        this.stmtInsertSale.run(
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
         WHERE synced = 0`
      )
      .all();

    rows.sort((a, b) => compareHlcTimestamps(a.hlc_timestamp, b.hlc_timestamp));

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
    this.db.exec("BEGIN IMMEDIATE");
    try {
      for (const id of clientEventIds) {
        this.stmtMarkSynced.run(id);
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
    ? `<div class="status-badge green"><span class="dot green"></span> Aloqa bor · Fiskal onlayn</div>`
    : `<div class="status-badge yellow"><span class="dot yellow"></span> ${escapeHtml(uzDictionary.offline.posOfflineBanner)}</div>`;

  const html = `
    <div class="pos-split-layout">
      <header class="pos-topbar">
        <div class="pos-store-info">
          <h1>${escapeHtml(pos.storeName)}</h1>
          <span class="pos-terminal-tag tabular-nums">Kassa: ${escapeHtml(pos.terminalId)} · CAS Tarozi: 1.250 kg</span>
        </div>
        ${statusBanner}
        <button type="button" class="btn-qr-inbound" data-action="pos-qr-inbound" style="min-height:${designTokens.spacing.minTouchTargetPosPx}px">
          Tovar qabul qilish (QR - F4)
        </button>
      </header>
      <div class="pos-columns">
        <section class="pos-left-catalog" aria-label="${escapeHtml(uzDictionary.catalog.products)}">
          <div class="pos-search-bar">
            <input type="search" placeholder="2D shtrix-kodni skanerlang yoki tovar nomini yozing (F2)" />
          </div>
          <div class="pos-tiles-grid">
            <button type="button" class="pos-product-tile" data-action="pos-tile" data-price="1897500" data-name="Kungaboqar yog'i Oliya 1L">
              <span class="tile-category">Yog'-moy</span>
              <strong>Kungaboqar yog'i Oliya 1L</strong>
              <span class="tile-price tabular-nums">18 975 so'm</span>
              <span class="status-badge green">Zahirada: 580 dona</span>
            </button>
            <button type="button" class="pos-product-tile" data-action="pos-tile" data-price="24500000" data-name="Birinchi navli bug'doy uni 50kg">
              <span class="tile-category">Un va don</span>
              <strong>Bug'doy uni 50 kg qop</strong>
              <span class="tile-price tabular-nums">245 000 so'm</span>
              <span class="status-badge green">Zahirada: 42 qop</span>
            </button>
            <button type="button" class="pos-product-tile" data-action="pos-tile" data-price="1400000" data-name="Shakar Oq Kristall 1kg (Tarozi)">
              <span class="tile-category">Tarozi (CAS)</span>
              <strong>Shakar Oq Kristall 1 kg</strong>
              <span class="tile-price tabular-nums">14 000 so'm</span>
              <span class="status-badge yellow">Zahirada: 18 kg</span>
            </button>
            <button type="button" class="pos-product-tile" data-action="pos-tile" data-price="950000" data-name="Sut Musaffo 1L 3.2%">
              <span class="tile-category">Sut mahsulotlari</span>
              <strong>Sut Musaffo 1L (3.2%)</strong>
              <span class="tile-price tabular-nums">9 500 so'm</span>
              <span class="status-badge red">Zahirada: 4 dona</span>
            </button>
          </div>
        </section>
        <section class="pos-right-receipt" aria-label="Chek">
          <div class="receipt-header">
            <strong>Joriy kassa cheki #1042</strong>
            <span class="tabular-nums">QQS 12% ichida</span>
          </div>
          <div class="receipt-lines" id="pos-receipt-lines">
            <div class="receipt-line">
              <div>
                <strong>Kungaboqar yog'i Oliya 1L</strong>
                <small class="tabular-nums">1 dona × 18 975 so'm</small>
              </div>
              <strong class="tabular-nums">18 975 so'm</strong>
            </div>
            <div class="receipt-line">
              <div>
                <strong>Sut Musaffo 1L (3.2%)</strong>
                <small class="tabular-nums">17 dona × 9 766.18 so'm</small>
              </div>
              <strong class="tabular-nums">166 025 so'm</strong>
            </div>
          </div>
          <div class="pos-payment-modes" role="radiogroup" aria-label="To'lov turi">
            <button type="button" class="pay-mode active">Naqd (F5)</button>
            <button type="button" class="pay-mode">Karta (F6)</button>
            <button type="button" class="pay-mode">Aralash (F7)</button>
            <button type="button" class="pay-mode">Nasiya daftari (F8)</button>
          </div>
          <div class="receipt-summary">
            <span>Jami to'lovga:</span>
            <div class="receipt-total tabular-nums" id="pos-total-display">${escapeHtml(formatTiyinUzs(currentTotalTiyin))}</div>
          </div>
          <button type="button" class="btn-pos-pay" data-primary-cta="true" data-action="pos-pay" style="min-height:${designTokens.spacing.minTouchTargetPosPx}px">
            TO'LASH (F12)
          </button>
        </section>
      </div>
    </div>
  `;

  assertZeroJargonInText(html.replace(/<[^>]+>/g, " "));
  return html;
}
