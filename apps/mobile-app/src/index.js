/**
 * DBazar Minimalist Mobile Application (`apps/mobile-app`)
 * Redesigned single-handed mobile interface:
 * - Strict maximum 4 Bottom Tabs ("Tovarlar", "Savat", "Buyurtmalar", "Yetkazish")
 * - 48px+ touch targets
 * - Buyer/Sales Agent mode & Driver Live GPS + 1-Button POD mode
 */
import crypto from "node:crypto";
import {
  assertZeroJargonInText,
  designTokens,
  uzDictionary,
} from "../../../packages/ui-tokens/src/index.js";
import {
  calculateTieredPriceTiyin,
  escapeHtml,
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
      (t, idx) =>
        `<button type="button" class="bottom-tab ${(app.mode === "DRIVER" && idx === 3) || (app.mode !== "DRIVER" && idx === 0) ? "active" : ""}" style="min-height:${designTokens.spacing.minTouchTargetMobilePx}px">${escapeHtml(t)}</button>`
    )
    .join("");

  const bodyHtml =
    app.mode === "DRIVER" && app.activeDelivery
      ? `
        <section class="driver-screen" aria-label="Yetkazib berish">
          <div class="mobile-status-bar">
            <span class="status-badge yellow"><i class="dot yellow"></i> Jonli GPS yoqilgan</span>
            <span class="tabular-nums">41.3111° N, 69.2406° E</span>
          </div>
          <div class="driver-map-card">
            <div class="map-route-line"></div>
            <div class="map-pin origin">Ombor</div>
            <div class="map-pin destination">Mijoz (2.4 km)</div>
          </div>
          <div class="driver-customer-card">
            <span class="drawer-eyebrow">Joriy manzil</span>
            <h2>${escapeHtml(app.activeDelivery.customerName)}</h2>
            <p>${escapeHtml(app.activeDelivery.address)}</p>
            <a href="tel:${escapeHtml(app.activeDelivery.customerPhone)}" class="btn-secondary btn-call" style="min-height:${designTokens.spacing.minTouchTargetMobilePx}px">
              Mijozga qo'ng'iroq qilish (${escapeHtml(app.activeDelivery.customerPhone)})
            </a>
          </div>
          <div class="driver-pod-box">
            <label for="mobile-otp-input">Mijozdagi 6 xonali tasdiqlash kodi:</label>
            <input id="mobile-otp-input" type="text" maxlength="6" value="482910" class="tabular-nums" />
          </div>
          <button type="button" class="btn-primary-cta driver-main-cta" data-primary-cta="true" data-action="driver-step" style="min-height:${designTokens.spacing.minTouchTargetPosPx}px">
            ${escapeHtml(app.getDriverPrimaryButtonLabel())}
          </button>
        </section>
      `
      : `
        <section class="buyer-screen" aria-label="${escapeHtml(uzDictionary.catalog.products)}">
          <div class="mobile-header">
            <strong>Baraka Minimarket</strong>
            <span class="status-badge green"><i class="dot green"></i> Nasiya: 5 000 000 so'm</span>
          </div>
          <input type="search" placeholder="Tovar qidirish yoki shtrix-kod skaneri" />
          <div class="mobile-product-list">
            <article class="mobile-product-card">
              <div>
                <strong>Kungaboqar yog'i Oliya (1L)</strong>
                <p class="tabular-nums">50+ donada: 16 500 so'm</p>
              </div>
              <button type="button" class="btn-secondary mobile-plus-btn" data-action="mobile-add" data-price="1650000" style="min-height:${designTokens.spacing.minTouchTargetMobilePx}px;min-width:${designTokens.spacing.minTouchTargetMobilePx}px">+</button>
            </article>
            <article class="mobile-product-card">
              <div>
                <strong>Birinchi navli bug'doy uni (50 kg)</strong>
                <p class="tabular-nums">10+ qopda: 210 000 so'm</p>
              </div>
              <button type="button" class="btn-secondary mobile-plus-btn" data-action="mobile-add" data-price="21000000" style="min-height:${designTokens.spacing.minTouchTargetMobilePx}px;min-width:${designTokens.spacing.minTouchTargetMobilePx}px">+</button>
            </article>
          </div>
          <div class="mobile-checkout-bar">
            <div>
              <span>Jami savatda:</span>
              <div class="cart-summary tabular-nums" id="mobile-cart-total">${escapeHtml(formatTiyinUzs(app.getCartTotalTiyin()))}</div>
            </div>
            <button type="button" class="btn-primary-cta" data-primary-cta="true" style="min-height:${designTokens.spacing.minTouchTargetMobilePx}px">
              ${escapeHtml(uzDictionary.billing.safePayment)}
            </button>
          </div>
        </section>
      `;

  const html = `
    <div class="mobile-shell">
      <div class="mobile-notch"></div>
      <main>${bodyHtml}</main>
      <nav class="bottom-tab-bar" aria-label="Pastki menyu">${tabsHtml}</nav>
    </div>
  `;

  assertZeroJargonInText(html.replace(/<[^>]+>/g, " "));
  return html;
}
