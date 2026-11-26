/**
 * DBazar Minimalist Mobile Application (`apps/mobile-app`)
 * Strict maximum 4 Bottom Tabs, 48px+ buttons, Buyer/Agent & Driver GPS/POD modes.
 */
import crypto from "node:crypto";
import {
  assertZeroJargonInText,
  designTokens,
  uzDictionary,
} from "../../../packages/ui-tokens/src/index.js";
import {
  calculateTieredPriceTiyin,
  formatTiyinUzs,
} from "../../../packages/shared-utils/src/index.js";

export const MOBILE_BOTTOM_TABS = [
  uzDictionary.catalog.products,
  "Savat",
  "Buyurtmalar",
  "Yetkazish",
];

export class MobileAppController {
  constructor(mode = "BUYER_OR_AGENT") {
    this.mode = mode;
    this.isOnline = true;
    this.cart = new Map();
    this.offlineQueue = [];
    this.activeDelivery = null;
  }

  getBottomTabs() {
    if (MOBILE_BOTTOM_TABS.length > 4) {
      throw new Error("Mobil UX qoidabuzarligi: Pastki menyuda 4 tadan ko'p tab bo'lishi mumkin emas.");
    }
    return MOBILE_BOTTOM_TABS;
  }

  tapAddProduct(offer, incrementQty) {
    const add = incrementQty ?? offer.min_order_qty;
    const current = this.cart.get(offer.id)?.quantity ?? 0;
    const nextQty = current + add;
    const { totalPriceTiyin } = calculateTieredPriceTiyin(
      offer.base_price_tiyin,
      offer.price_tiers,
      nextQty
    );
    this.cart.set(offer.id, { offer, quantity: nextQty, lineTotalTiyin: totalPriceTiyin });
    return totalPriceTiyin;
  }

  getCartTotalTiyin() {
    let sum = 0;
    for (const entry of this.cart.values()) {
      sum += entry.lineTotalTiyin;
    }
    return sum;
  }

  getDriverPrimaryButtonLabel() {
    if (!this.activeDelivery) return uzDictionary.logistics.pickedUp;
    switch (this.activeDelivery.status) {
      case "ASSIGNED":
        return uzDictionary.logistics.pickedUp;
      case "PICKED_UP":
        return uzDictionary.logistics.inTransit;
      case "IN_TRANSIT":
      case "DELIVERED":
        return uzDictionary.logistics.delivered;
    }
  }

  recordDriverGpsPing(latMicrodeg, lngMicrodeg) {
    if (!Number.isInteger(latMicrodeg) || !Number.isInteger(lngMicrodeg)) {
      throw new Error("GPS koordinatalari butun mikrogradusda (lat * 1e6) bo'lishi shart.");
    }
    if (!this.activeDelivery) {
      throw new Error("Faol yetkazib berish mavjud emas.");
    }
    this.activeDelivery.latMicrodeg = latMicrodeg;
    this.activeDelivery.lngMicrodeg = lngMicrodeg;

    if (!this.isOnline) {
      this.offlineQueue.push({
        id: crypto.randomUUID(),
        type: "GPS_PING",
        payload: {
          shipment_id: this.activeDelivery.shipmentId,
          lat_microdeg: latMicrodeg,
          lng_microdeg: lngMicrodeg,
        },
        createdAtMs: Date.now(),
      });
    }
  }

  advanceDriverStatusOneButton(podInput) {
    if (!this.activeDelivery) {
      throw new Error("Faol yetkazib berish tanlanmagan.");
    }
    if (this.activeDelivery.status === "ASSIGNED") {
      this.activeDelivery.status = "PICKED_UP";
      return this.activeDelivery.status;
    }
    if (this.activeDelivery.status === "PICKED_UP") {
      this.activeDelivery.status = "IN_TRANSIT";
      return this.activeDelivery.status;
    }
    if (this.activeDelivery.status === "IN_TRANSIT") {
      if (!podInput || !/^\d{6}$/.test(podInput.otpCode)) {
        throw new Error("Yukni topshirish uchun mijozning 6 xonali tasdiqlash kodini kiriting.");
      }
      this.activeDelivery.status = "DELIVERED";
      if (!this.isOnline) {
        this.offlineQueue.push({
          id: crypto.randomUUID(),
          type: "CONFIRM_POD",
          payload: {
            shipment_id: this.activeDelivery.shipmentId,
            pod_otp_code: podInput.otpCode,
            pod_photo_url: podInput.photoUrl,
          },
          createdAtMs: Date.now(),
        });
      }
      return this.activeDelivery.status;
    }
    return "DELIVERED";
  }

  flushOfflineQueue() {
    const flushed = [...this.offlineQueue];
    this.offlineQueue = [];
    this.isOnline = true;
    return flushed;
  }
}

export function renderMobileScreenHtml(app) {
  const tabsHtml = app
    .getBottomTabs()
    .map(
      (t) =>
        `<button type="button" class="bottom-tab" style="min-height:${designTokens.spacing.minTouchTargetMobilePx}px">${t}</button>`
    )
    .join("");

  const bodyHtml =
    app.mode === "DRIVER" && app.activeDelivery
      ? `
        <section class="driver-screen" aria-label="Yetkazib berish">
          <h2>${app.activeDelivery.customerName}</h2>
          <p>${app.activeDelivery.address}</p>
          <a href="tel:${app.activeDelivery.customerPhone}" class="btn-call" style="min-height:${designTokens.spacing.minTouchTargetMobilePx}px">
            Mijozga qo'ng'iroq qilish
          </a>
          <button type="button" class="btn-primary-cta" data-primary-cta="true" style="min-height:${designTokens.spacing.minTouchTargetMobilePx}px">
            ${app.getDriverPrimaryButtonLabel()}
          </button>
        </section>
      `
      : `
        <section class="buyer-screen" aria-label="${uzDictionary.catalog.products}">
          <input type="search" placeholder="Tovar qidirish yoki shtrix-kod skaneri" />
          <div class="cart-summary tabular-nums">${formatTiyinUzs(app.getCartTotalTiyin())}</div>
          <button type="button" class="btn-primary-cta" data-primary-cta="true" style="min-height:${designTokens.spacing.minTouchTargetMobilePx}px">
            ${uzDictionary.billing.safePayment}
          </button>
        </section>
      `;

  const html = `
    <div class="mobile-shell">
      <main>${bodyHtml}</main>
      <nav class="bottom-tab-bar" aria-label="Pastki menyu">${tabsHtml}</nav>
    </div>
  `;

  assertZeroJargonInText(html.replace(/<[^>]+>/g, " "));
  return html;
}
