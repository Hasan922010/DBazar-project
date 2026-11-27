import test from "node:test";
import assert from "node:assert/strict";
import { MobileAppController, renderMobileScreenHtml } from "../src/index.js";
import { SAMPLE_OFFER } from "../../../packages/shared-utils/src/index.js";

test("Mobile App: 4 Bottom Tabs limit, Buyer/Agent Cart & Driver 1-Button GPS + OTP POD flow", () => {
  const buyerApp = new MobileAppController("BUYER_OR_AGENT");
  assert.equal(buyerApp.getBottomTabs().length, 4);

  buyerApp.tapAddProduct(SAMPLE_OFFER, 25);
  buyerApp.tapAddProduct(SAMPLE_OFFER, 25);
  assert.equal(buyerApp.getCartTotalTiyin(), 82_500_000);

  const buyerHtml = renderMobileScreenHtml(buyerApp);
  assert.match(buyerHtml, /Xavfsiz to'lov/);
  assert.match(buyerHtml, /825 000 so'm/);

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
