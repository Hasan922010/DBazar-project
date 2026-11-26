import test from "node:test";
import assert from "node:assert/strict";
import { MobileAppController, renderMobileScreenHtml } from "../src/index.js";

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

test("Mobile App: 4 Bottom Tabs limit, Buyer/Agent Cart & Driver 1-Button GPS + OTP POD flow", () => {
  const buyerApp = new MobileAppController("BUYER_OR_AGENT");
  assert.equal(buyerApp.getBottomTabs().length, 4);

  buyerApp.tapAddProduct(SAMPLE_OFFER, 25);
  buyerApp.tapAddProduct(SAMPLE_OFFER, 25); // reaches 50 tier -> 50 * 1,650,000 = 82,500,000 tiyin
  assert.equal(buyerApp.getCartTotalTiyin(), 82_500_000);

  const buyerHtml = renderMobileScreenHtml(buyerApp);
  assert.match(buyerHtml, /Xavfsiz to'lov/);
  assert.match(buyerHtml, /825 000 so'm/);

  // Driver Mode: 1-Button step-by-step transition ("Ombordan oldim" -> "Yo'lga chiqdim" -> "Topshirdim")
  const driverApp = new MobileAppController("DRIVER");
  driverApp.activeDelivery = {
    shipmentId: "99999999-9999-9999-9999-999999999999",
    subOrderId: "88888888-8888-8888-8888-888888888888",
    customerName: "Baraka Minimarket #1",
    customerPhone: "+998904440044",
    address: "Toshkent sh., Chilonzor-9",
    status: "ASSIGNED",
    latMicrodeg: 41311081,
    lngMicrodeg: 69240562,
  };

  assert.equal(driverApp.getDriverPrimaryButtonLabel(), "Ombordan oldim");
  assert.equal(driverApp.advanceDriverStatusOneButton(), "PICKED_UP");
  assert.equal(driverApp.getDriverPrimaryButtonLabel(), "Yo'lga chiqdim");
  assert.equal(driverApp.advanceDriverStatusOneButton(), "IN_TRANSIT");
  assert.equal(driverApp.getDriverPrimaryButtonLabel(), "Topshirdim");

  // Offline GPS ping & OTP POD queueing
  driverApp.isOnline = false;
  driverApp.recordDriverGpsPing(41315000, 69245000);

  assert.throws(
    () => driverApp.advanceDriverStatusOneButton({ otpCode: "12", photoUrl: "" }),
    /6 xonali/
  );
  assert.equal(
    driverApp.advanceDriverStatusOneButton({
      otpCode: "482910",
      photoUrl: "https://minio.dbazar.uz/pod/mobile-pod.jpg",
    }),
    "DELIVERED"
  );

  assert.equal(driverApp.offlineQueue.length, 2);
  const flushed = driverApp.flushOfflineQueue();
  assert.equal(flushed.length, 2);
  assert.equal(driverApp.offlineQueue.length, 0);
});
