import test from "node:test";
import assert from "node:assert/strict";
import { WebPortalStore, renderCabinetHtml } from "../src/index.js";
import { assertZeroJargonInText } from "../../../packages/ui-tokens/src/index.js";

const SAMPLE_OFFER = {
  id: "11111111-1111-1111-1111-111111111111",
  seller_id: "22222222-2222-2222-2222-222222222222",
  seller_name: "Roison Foods Factory",
  base_price_tiyin: 1_800_000,
  min_order_qty: 10,
  price_tiers: [
    { min_qty: 10, max_qty: 49, unit_price_tiyin: 1_800_000 },
    { min_qty: 50, max_qty: null, unit_price_tiyin: 1_650_000 },
  ],
  variant: {
    id: "33333333-3333-3333-3333-333333333333",
    product_id: "44444444-4444-4444-4444-444444444444",
    product_name: "Kungaboqar yog'i Oliya",
    brand: "Oliya",
    sku: "OLIYA-1L",
    variant_name: "1 Litr PET",
    mxik_code: "01901001001000001",
    barcode: "4780010010011",
    unit_type: "LITER",
    packaging_coefficient: 12,
    weight_grams: 920,
  },
};

test("Web-Portal Manufacturer 3-step product form, VMI Traffic-Light cards & zero jargon", () => {
  const mfg = new WebPortalStore("MANUFACTURER");
  assert.equal(mfg.getSidebarMenu().length, 5);

  mfg.submitManufacturerStep1("Kungaboqar yog'i Oliya", "Oliya", "1 Litr PET");
  assert.equal(mfg.wizard.step, 2);

  assert.throws(() => mfg.submitManufacturerStep2("12345", "478001"), /17 ta raqam/);
  mfg.submitManufacturerStep2("01901001001000001", "4780010010011", 12);
  assert.equal(mfg.wizard.step, 3);

  const completed = mfg.submitManufacturerStep3(1_800_000, [
    { min_qty: 50, max_qty: null, unit_price_tiyin: 1_650_000 },
  ]);
  assert.equal(completed.basePriceTiyin, 1_800_000);

  const html = renderCabinetHtml(mfg, {
    vmi: {
      total_store_stock_qty: 420,
      total_sold_qty: 185,
      low_stock_alert_count: 2,
      items: [],
    },
  });
  assert.match(html, /Do'kondagi qoldiq/);
  assert.match(html, /Kunlik sotuv/);
  assert.match(html, /Tez tugaydigan tovarlar/);
  assert.match(html, /tabular-nums/);
});

test("Web-Portal Buyer 1-Click Add to Cart, Tiered Pricing & Progressive Disclosure Drawer", () => {
  const buyer = new WebPortalStore("CUSTOMER");
  buyer.setTheme("dark");

  // First click adds 30 units at 1,800,000 tiyin
  const line1 = buyer.addToCartOneClick(SAMPLE_OFFER, 30);
  assert.equal(line1.unitPriceTiyin, 1_800_000);

  // Second click adds 30 units -> total 60 units -> automatically drops to 1,650,000 tiyin tier!
  const line2 = buyer.addToCartOneClick(SAMPLE_OFFER, 30);
  assert.equal(line2.quantity, 60);
  assert.equal(line2.unitPriceTiyin, 1_650_000);
  assert.equal(buyer.getCartTotalTiyin(), 99_000_000);

  // Before opening Drawer, 17-digit MXIK code is hidden from main table
  const closedHtml = renderCabinetHtml(buyer, { offers: [SAMPLE_OFFER] });
  assert.equal(closedHtml.includes("01901001001000001"), false);

  // Opening "Batafsil" Drawer reveals 17-digit MXIK and batch_id
  buyer.openDetailsDrawer(SAMPLE_OFFER, "BATCH-OIL-2026-11");
  const openHtml = renderCabinetHtml(buyer, { offers: [SAMPLE_OFFER] });
  assert.equal(openHtml.includes("01901001001000001"), true);
  assert.equal(openHtml.includes("BATCH-OIL-2026-11"), true);

  // Zero-jargon guard rejects forbidden technical terms
  assert.throws(() => assertZeroJargonInText("Escrow to'lovi"), /UI Jargon/);
});
