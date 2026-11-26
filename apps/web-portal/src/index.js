/**
 * DBazar Minimalist Web-Portal (`apps/web-portal`)
 * Implements the 3 B2B role cabinets following `apps/web-portal/AGENTS.md`,
 * `agency-ux-architect`, `agency-frontend-developer`, and `/ui-minimalist-design`.
 */
import {
  assertZeroJargonInText,
  designTokens,
  resolveThemeAttribute,
  uzDictionary,
} from "../../../packages/ui-tokens/src/index.js";
import {
  calculateTieredPriceTiyin,
  formatTiyinUzs,
  isValidMxikCode,
} from "../../../packages/shared-utils/src/index.js";

const SIDEBAR_MENUS = {
  MANUFACTURER: ["Asosiy ko'rsatkichlar", "Tovarlar", "Narx pog'onalari", "Dilerlar", "Sozlamalar"],
  INTERMEDIARY: ["Do'kondagi qoldiq", "Kelgan buyurtmalar", "Ombor", "Nasiya limitlari", "Sozlamalar"],
  CUSTOMER: ["Tovarlar", "Narxlarni solishtirish", "Savat", "Buyurtmalarim", "Nasiya"],
};

export class WebPortalStore {
  constructor(role) {
    this.role = role;
    this.theme = "system";
    this.drawer = null;
    this.wizard = {
      step: 1,
      name: "",
      brand: "",
      variantName: "",
      mxikCode: "",
      barcode: "",
      packagingCoefficient: 1,
      basePriceTiyin: 0,
      tiers: [],
    };
    this.cart = new Map();
    this.confirmedOrderIds = new Set();
  }

  getSidebarMenu() {
    const items = SIDEBAR_MENUS[this.role];
    if (!items || items.length > 6) {
      throw new Error("UX qoidabuzarligi: Chap menyuda 6 tadan ko'p band bo'lishi mumkin emas.");
    }
    return items;
  }

  setTheme(mode) {
    this.theme = mode;
    return resolveThemeAttribute(mode);
  }

  openDetailsDrawer(offer, batchId = "BATCH-2026-11") {
    this.drawer = {
      isOpen: true,
      productName: `${offer.variant.product_name} (${offer.variant.variant_name})`,
      mxikCode: offer.variant.mxik_code,
      barcode: offer.variant.barcode,
      batchId,
      packagingCoefficient: offer.variant.packaging_coefficient,
      vatRatePercent: 12,
    };
    return this.drawer;
  }

  closeDetailsDrawer() {
    this.drawer = null;
  }

  submitManufacturerStep1(name, brand, variantName) {
    if (!name || name.trim().length < 2) throw new Error("Tovar nomini kiriting.");
    this.wizard.name = name.trim();
    this.wizard.brand = (brand || "").trim();
    this.wizard.variantName = (variantName || "").trim();
    this.wizard.step = 2;
  }

  submitManufacturerStep2(mxikCode, barcode, packagingCoefficient = 1) {
    if (!isValidMxikCode(mxikCode)) {
      throw new Error("Katalog kodi 17 ta raqamdan iborat bo'lishi shart.");
    }
    this.wizard.mxikCode = mxikCode;
    this.wizard.barcode = (barcode || "").trim();
    this.wizard.packagingCoefficient = Math.max(1, Math.trunc(packagingCoefficient));
    this.wizard.step = 3;
  }

  submitManufacturerStep3(basePriceTiyin, tiers = []) {
    if (!Number.isInteger(basePriceTiyin) || basePriceTiyin <= 0) {
      throw new Error("Narx 0 tiyindan katta butun son bo'lishi shart.");
    }
    this.wizard.basePriceTiyin = basePriceTiyin;
    this.wizard.tiers = tiers;
    return { ...this.wizard };
  }

  confirmIncomingOrderOneClick(subOrder) {
    this.confirmedOrderIds.add(subOrder.id);
    return {
      subOrderId: subOrder.id,
      status: "CONFIRMED",
      formattedTotal: formatTiyinUzs(subOrder.subtotal_amount_tiyin),
    };
  }

  addToCartOneClick(offer, addQty) {
    const stepQty = addQty ?? offer.min_order_qty;
    const existing = this.cart.get(offer.id);
    const nextQty = (existing ? existing.quantity : 0) + stepQty;
    const { unitPriceTiyin, totalPriceTiyin } = calculateTieredPriceTiyin(
      offer.base_price_tiyin,
      offer.price_tiers,
      nextQty
    );

    const line = {
      offerId: offer.id,
      productName: `${offer.variant.product_name} (${offer.variant.variant_name})`,
      sellerName: offer.seller_name,
      quantity: nextQty,
      unitPriceTiyin,
      lineTotalTiyin: totalPriceTiyin,
    };
    this.cart.set(offer.id, line);
    return line;
  }

  getCartTotalTiyin() {
    let total = 0;
    for (const line of this.cart.values()) {
      total += line.lineTotalTiyin;
    }
    return total;
  }
}

export function renderCabinetHtml(store, options = {}) {
  const menuItems = store.getSidebarMenu();
  const primaryCtaLabel =
    store.role === "MANUFACTURER"
      ? "Tovar qo'shish"
      : store.role === "INTERMEDIARY"
        ? "Buyurtmani tasdiqlash"
        : uzDictionary.billing.safePayment;

  const kpiCardsHtml = options.vmi
    ? `
      <section class="kpi-grid" aria-label="Asosiy ko'rsatkichlar">
        <article class="kpi-card" data-status="GREEN">
          <span>${uzDictionary.inventory.storeStock}</span>
          <strong class="tabular-nums">${options.vmi.total_store_stock_qty} dona</strong>
        </article>
        <article class="kpi-card" data-status="YELLOW">
          <span>${uzDictionary.inventory.dailySales}</span>
          <strong class="tabular-nums">${options.vmi.total_sold_qty} dona</strong>
        </article>
        <article class="kpi-card" data-status="RED">
          <span>${uzDictionary.inventory.lowStock}</span>
          <strong class="tabular-nums">${options.vmi.low_stock_alert_count} ta</strong>
        </article>
      </section>
    `
    : "";

  const offersRowsHtml = (options.offers || [])
    .map(
      (o) => `
      <div role="row" class="table-row">
        <div role="cell">${o.variant.product_name} (${o.variant.variant_name})</div>
        <div role="cell">${o.seller_name}</div>
        <div role="cell" class="tabular-nums">${formatTiyinUzs(o.base_price_tiyin)}</div>
        <div role="cell">
          <button type="button" class="btn-secondary" data-action="drawer">${uzDictionary.catalog.details}</button>
          <button type="button" class="btn-primary-cta" style="min-height:${designTokens.spacing.minTouchTargetMobilePx}px">${uzDictionary.catalog.addToCart}</button>
        </div>
      </div>`
    )
    .join("");

  const drawerHtml = store.drawer?.isOpen
    ? `
      <aside role="dialog" aria-label="${uzDictionary.catalog.details}" class="side-drawer">
        <h3>${store.drawer.productName}</h3>
        <p>Soliq katalog kodi: <span class="tabular-nums">${store.drawer.mxikCode}</span></p>
        <p>Shtrix-kod: <span class="tabular-nums">${store.drawer.barcode}</span></p>
        <p>Partiya: <span>${store.drawer.batchId}</span></p>
        <p>Qadoqda: <span class="tabular-nums">${store.drawer.packagingCoefficient} dona</span></p>
      </aside>
    `
    : "";

  const html = `
    <div class="web-portal-layout" data-theme="${resolveThemeAttribute(store.theme)}">
      <nav aria-label="Asosiy menyu" class="sidebar">
        <ul>${menuItems.map((m) => `<li>${m}</li>`).join("")}</ul>
      </nav>
      <main class="content">
        <header class="topbar">
          <div class="theme-toggle" role="radiogroup" aria-label="Mavzu tanlash">
            <button type="button" data-theme="light">Yorug'</button>
            <button type="button" data-theme="dark">Tungi</button>
            <button type="button" data-theme="system">Avto</button>
          </div>
          <button type="button" class="btn-primary-cta" data-primary-cta="true" style="min-height:${designTokens.spacing.minTouchTargetMobilePx}px">
            ${primaryCtaLabel}
          </button>
        </header>
        ${kpiCardsHtml}
        <div role="table" aria-label="${uzDictionary.catalog.products}">
          ${offersRowsHtml}
        </div>
        ${drawerHtml}
      </main>
    </div>
  `;

  assertZeroJargonInText(html.replace(/<[^>]+>/g, " "));
  return html;
}
