import test from "node:test";
import assert from "node:assert/strict";
import { WebPortalStore, renderCabinetHtml } from "../src/index.js";
import { assertZeroJargonInText } from "../../../packages/ui-tokens/src/index.js";
import { SAMPLE_OFFER } from "../../../packages/shared-utils/src/index.js";

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

test("Web-Portal Buyer 1-Click Add to Cart, Tiered Pricing, Progressive Disclosure Drawer & XSS escaping", () => {
  const buyer = new WebPortalStore("CUSTOMER");
  buyer.setTheme("dark");

  const line1 = buyer.addToCartOneClick(SAMPLE_OFFER, 30);
  assert.equal(line1.unitPriceTiyin, 1_800_000);

  const line2 = buyer.addToCartOneClick(SAMPLE_OFFER, 30);
  assert.equal(line2.quantity, 60);
  assert.equal(line2.unitPriceTiyin, 1_650_000);
  assert.equal(buyer.getCartTotalTiyin(), 99_000_000);

  const closedHtml = renderCabinetHtml(buyer, { offers: [SAMPLE_OFFER] });
  assert.equal(closedHtml.includes("01901001001000001"), false);

  buyer.openDetailsDrawer(SAMPLE_OFFER, "BATCH-OIL-2026-11");
  const openHtml = renderCabinetHtml(buyer, { offers: [SAMPLE_OFFER] });
  assert.equal(openHtml.includes("01901001001000001"), true);
  assert.equal(openHtml.includes("BATCH-OIL-2026-11"), true);

  // XSS Escaping check (Fix #1)
  const xssOffer = {
    ...SAMPLE_OFFER,
    seller_name: 'Seller <script>alert("xss")</script>',
  };
  const safeHtml = renderCabinetHtml(buyer, { offers: [xssOffer] });
  assert.equal(safeHtml.includes("<script>"), false);
  assert.equal(safeHtml.includes("&lt;script&gt;"), true);

  assert.throws(() => assertZeroJargonInText("Escrow to'lovi"), /UI Jargon/);
});
