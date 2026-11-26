import test from "node:test";
import assert from "node:assert/strict";
import { OfflinePosDatabase, renderPosScreenHtml } from "../src/index.js";
import { readCasScaleWeightGrams } from "../../../packages/mocks-and-emulators/pos-hardware-sim/src/index.js";

const SAMPLE_WAYBILL = {
  id: "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
  seller_org_id: "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
  seller_org_name: "Roison Foods Factory",
  status: "DELIVERED",
  subtotal_amount_tiyin: 99_000_000,
  waybill_qr_token: "WB-ROISON20261126",
  is_pos_inbounded: false,
  items: [
    {
      id: "cccccccc-cccc-cccc-cccc-cccccccccccc",
      variant_id: "dddddddd-dddd-dddd-dddd-dddddddddddd",
      sku: "OLIYA-1L",
      product_name: "Kungaboqar yog'i Oliya (1 Litr PET)",
      mxik_code: "01901001001000001",
      barcode: "4780010010011",
      batch_id: "BATCH-OIL-2026-11",
      quantity: 600,
      unit_price_tiyin: 1_650_000,
      line_total_tiyin: 990_000_000,
    },
  ],
};

test("Offline-First POS: 1-Click QR Waybill Auto-Inbound, 500 Offline Airplane Mode Sales/Returns & Hardware Sim", () => {
  const pos = new OfflinePosDatabase({
    storeId: "eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee",
    terminalId: "TERM-BARAKA-01",
    storeName: "Baraka Minimarket Kassa #1",
  });

  // 1. 1-Click Auto-Inbound by scanning waybill QR (idempotent on duplicate scan)
  const inbound1 = pos.oneClickWaybillInbound(SAMPLE_WAYBILL);
  assert.equal(inbound1.inboundedItemsCount, 1);
  const inboundDup = pos.oneClickWaybillInbound(SAMPLE_WAYBILL);
  assert.equal(inboundDup.inboundedItemsCount, 0);

  const variantId = SAMPLE_WAYBILL.items[0].variant_id;
  assert.equal(pos.getVariantStockQty(variantId), 600);

  // 2. Airplane Mode: Disconnect internet and execute 500 sequential sales & returns
  pos.isOnline = false;
  const offlineScreen = renderPosScreenHtml(pos, 1_897_500);
  assert.match(offlineScreen, /Internet uzildi — kassa oflayn ishlashda davom etmoqda/);
  assert.match(offlineScreen, /TO'LASH \(F12\)/);

  let lastReceipt = null;
  for (let i = 0; i < 500; i++) {
    const isReturn = i % 10 === 9; // 450 SALE (-450), 50 RETURN (+50) => net -400
    const res = pos.recordCheckoutEvent({
      variantId,
      quantity: 1,
      eventType: isReturn ? "RETURN" : "SALE",
      paymentMethod: i % 5 === 0 ? "NASIYA" : "CASH",
      customerName: i % 5 === 0 ? "Doimiy Mijoz" : "",
      nowMs: 1764180000000 + i,
    });
    lastReceipt = res.receipt;
  }

  // Remaining stock computed strictly from append-only pos_stock_events: 600 - 450 + 50 = 200
  assert.equal(pos.getVariantStockQty(variantId), 200);
  assert.ok(lastReceipt.textPreview.includes("MXIK: 01901001001000001"));
  assert.ok(lastReceipt.rawBytes.length > 32);

  // 3. Hardware scale check
  const scale = readCasScaleWeightGrams("PLU-01", 1500);
  assert.equal(scale.weightGrams, 1500);
  assert.equal(scale.stable, true);

  // 4. Reconnect and export Delta-Sync batch (1 inbound + 500 checkout events = 501 events)
  pos.isOnline = true;
  const deltaBatch = pos.exportUnsyncedDeltaBatch();
  assert.equal(deltaBatch.events.length, 501);

  pos.markEventsSynced(deltaBatch.events.map((e) => e.client_event_id));
  assert.equal(pos.exportUnsyncedDeltaBatch().events.length, 0);
});
