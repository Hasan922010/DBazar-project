/**
 * DBazar Minimalist Web-Portal (`apps/web-portal`)
 * Redesigned with `agency-ux-architect`, `agency-ui-designer`, and `agency-frontend-developer`.
 * Enforces `/ui-minimalist-design`:
 * - Max 5 sidebar navigation items with clear active indicator
 * - Max 3 large Traffic-Light KPI cards (`tabular-nums`)
 * - 1 unmistakable Primary CTA per cabinet (`48px+`)
 * - Progressive Disclosure: 17-digit MXIK, barcode, batch_id & VAT details inside the "Batafsil" Side Drawer
 */
import {
  assertZeroJargonInText,
  designTokens,
  resolveThemeAttribute,
  uzDictionary,
} from "../../../packages/ui-tokens/src/index.js";
import {
  calculateTieredPriceTiyin,
  escapeHtml,
  formatTiyinUzs,
  isValidMxikCode,
} from "../../../packages/shared-utils/src/index.js";

const SIDEBAR_MENUS = {
  MANUFACTURER: ["Asosiy ko'rsatkichlar", "Tovarlar", "Narx pog'onalari", "Dilerlar", "Sozlamalar"],
  INTERMEDIARY: ["Do'kondagi qoldiq", "Kelgan buyurtmalar", "Ombor", "Nasiya limitlari", "Sozlamalar"],
  CUSTOMER: ["Tovarlar", "Narxlarni solishtirish", "Savat", "Buyurtmalarim", "Nasiya"],
};

const ROLE_META = {
  MANUFACTURER: {
    badge: "Ishlab chiqaruvchi kabineti",
    orgName: "Roison Foods Factory MChJ",
    subtitle: "Ulgurji narx pog'onalari va do'konlardagi sotuv tahlili",
  },
  INTERMEDIARY: {
    badge: "Distribyutor kabineti",
    orgName: "Tashkent Agro Distribyutor",
    subtitle: "Hududiy do'konlar qoldig'i va kelgan buyurtmalarni 1 bosishda tasdiqlash",
  },
  CUSTOMER: {
    badge: "Xaridor savdo portali",
    orgName: "Baraka Minimarket #1",
    subtitle: "Zavod va dilerlar narxini solishtirib, xavfsiz to'lov orqali buyurtma berish",
  },
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
  const meta = ROLE_META[store.role] || ROLE_META.CUSTOMER;
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
          <div class="kpi-header">
            <span>${escapeHtml(uzDictionary.inventory.storeStock)}</span>
            <span class="status-badge green"><i class="dot green"></i> Yetarli</span>
          </div>
          <strong class="tabular-nums">${Number(options.vmi.total_store_stock_qty)} dona</strong>
          <small class="kpi-caption">Hamkor do'konlar javonidagi faol qoldiq</small>
        </article>
        <article class="kpi-card" data-status="YELLOW">
          <div class="kpi-header">
            <span>${escapeHtml(uzDictionary.inventory.dailySales)}</span>
            <span class="status-badge yellow"><i class="dot yellow"></i> Jonli kassa</span>
          </div>
          <strong class="tabular-nums">${Number(options.vmi.total_sold_qty)} dona</strong>
          <small class="kpi-caption">Oxirgi smenada kassadan o'tgan sotuvlar</small>
        </article>
        <article class="kpi-card" data-status="RED">
          <div class="kpi-header">
            <span>${escapeHtml(uzDictionary.inventory.lowStock)}</span>
            <span class="status-badge red"><i class="dot red"></i> Yetkazish zarur</span>
          </div>
          <strong class="tabular-nums">${Number(options.vmi.low_stock_alert_count)} ta nuqta</strong>
          <small class="kpi-caption">Avto-buyurtma tayyorlangan do'konlar</small>
        </article>
      </section>
    `
    : "";

  const offersRowsHtml = (options.offers || [])
    .map((o) => {
      const bestTier =
        o.price_tiers && o.price_tiers.length > 0
          ? o.price_tiers[o.price_tiers.length - 1]
          : null;
      const tierBadge = bestTier
        ? `<span class="tier-pill tabular-nums">${Number(bestTier.min_qty)}+ donada: ${escapeHtml(formatTiyinUzs(bestTier.unit_price_tiyin))}</span>`
        : "";
      return `
      <div role="row" class="table-row" data-offer-id="${escapeHtml(o.id)}">
        <div role="cell" class="cell-product">
          <div class="product-avatar">${escapeHtml((o.variant.brand || o.variant.product_name || "T").slice(0, 1))}</div>
          <div>
            <div class="product-title">${escapeHtml(o.variant.product_name)} (${escapeHtml(o.variant.variant_name)})</div>
            <div class="product-meta">Minimal buyurtma: <span class="tabular-nums">${Number(o.min_order_qty)} dona</span> · Qadoqda <span class="tabular-nums">${Number(o.variant.packaging_coefficient)} dona</span></div>
          </div>
        </div>
        <div role="cell" class="cell-seller">
          <span class="seller-name">${escapeHtml(o.seller_name)}</span>
          <span class="status-badge green"><i class="dot green"></i> Tasdiqlangan</span>
        </div>
        <div role="cell" class="cell-price tabular-nums">
          <div class="base-price">${escapeHtml(formatTiyinUzs(o.base_price_tiyin))}</div>
          ${tierBadge}
        </div>
        <div role="cell" class="cell-actions">
          <button type="button" class="btn-secondary" data-action="drawer" data-offer-id="${escapeHtml(o.id)}">${escapeHtml(uzDictionary.catalog.details)}</button>
          <button type="button" class="btn-primary-cta" data-action="add-cart" data-offer-id="${escapeHtml(o.id)}" style="min-height:${designTokens.spacing.minTouchTargetMobilePx}px">${escapeHtml(uzDictionary.catalog.addToCart)}</button>
        </div>
      </div>`;
    })
    .join("");

  const drawerHtml = store.drawer?.isOpen
    ? `
      <aside role="dialog" aria-label="${escapeHtml(uzDictionary.catalog.details)}" class="side-drawer">
        <div class="drawer-header">
          <div>
            <span class="drawer-eyebrow">Soliq va partiya ma'lumotlari</span>
            <h3>${escapeHtml(store.drawer.productName)}</h3>
          </div>
          <button type="button" class="btn-secondary drawer-close" data-action="close-drawer">Yopish</button>
        </div>
        <div class="drawer-grid">
          <div class="drawer-item">
            <span>Soliq katalog kodi (17 xona)</span>
            <strong class="tabular-nums">${escapeHtml(store.drawer.mxikCode)}</strong>
          </div>
          <div class="drawer-item">
            <span>Shtrix-kod (EAN-13)</span>
            <strong class="tabular-nums">${escapeHtml(store.drawer.barcode)}</strong>
          </div>
          <div class="drawer-item">
            <span>Partiya raqami</span>
            <strong class="tabular-nums">${escapeHtml(store.drawer.batchId)}</strong>
          </div>
          <div class="drawer-item">
            <span>1 qadoqdagi miqdor</span>
            <strong class="tabular-nums">${Number(store.drawer.packagingCoefficient)} dona</strong>
          </div>
          <div class="drawer-item">
            <span>QQS stavkasi</span>
            <strong class="tabular-nums">${Number(store.drawer.vatRatePercent)}% (Elektron hisob-faktura tayyor)</strong>
          </div>
        </div>
      </aside>
    `
    : "";

  const html = `
    <div class="web-portal-layout" data-theme="${escapeHtml(resolveThemeAttribute(store.theme))}">
      <nav aria-label="Asosiy menyu" class="sidebar">
        <div class="brand-lockup">
          <div class="brand-logo">DB</div>
          <div>
            <strong>DBazar</strong>
            <span>Ulgurji Savdo Tizimi</span>
          </div>
        </div>
        <div class="role-chip">${escapeHtml(meta.badge)}</div>
        <ul>
          ${menuItems
            .map(
              (m, idx) =>
                `<li class="${idx === 0 ? "active" : ""}" tabindex="0">${escapeHtml(m)}</li>`
            )
            .join("")}
        </ul>
        <div class="sidebar-footer">
          <span class="status-badge green"><i class="dot green"></i> Xavfsiz to'lov himoyalangan</span>
        </div>
      </nav>
      <main class="content">
        <header class="topbar">
          <div class="topbar-titles">
            <h1>${escapeHtml(meta.orgName)}</h1>
            <p>${escapeHtml(meta.subtitle)}</p>
          </div>
          <div class="topbar-controls">
            <div class="theme-toggle" role="radiogroup" aria-label="Mavzu tanlash">
              <button type="button" data-theme="light" class="${store.theme === "light" ? "active" : ""}">Yorug'</button>
              <button type="button" data-theme="dark" class="${store.theme === "dark" ? "active" : ""}">Tungi</button>
              <button type="button" data-theme="system" class="${store.theme === "system" ? "active" : ""}">Avto</button>
            </div>
            <button type="button" class="btn-primary-cta" data-primary-cta="true" style="min-height:${designTokens.spacing.minTouchTargetMobilePx}px">
              ${escapeHtml(primaryCtaLabel)}
            </button>
          </div>
        </header>
        ${kpiCardsHtml}
        <section class="catalog-card">
          <div class="catalog-card-header">
            <div>
              <h2>${escapeHtml(uzDictionary.catalog.products)} va ulgurji narxlar</h2>
              <p>Hajmga qarab narx avtomatik arzonlashadi · Soliq kodlari "Batafsil" oynasida</p>
            </div>
            <div class="cart-pill tabular-nums" id="portal-cart-summary">
              Savatda: <strong id="portal-cart-total">${escapeHtml(formatTiyinUzs(store.getCartTotalTiyin()))}</strong>
            </div>
          </div>
          <div role="table" aria-label="${escapeHtml(uzDictionary.catalog.products)}" class="clean-table">
            ${offersRowsHtml}
          </div>
        </section>
        ${
          options.autoRestock && options.autoRestock.length > 0
            ? `
        <section class="catalog-card" style="margin-top:24px" aria-label="Avto-buyurtma tavsiyalari">
          <div class="catalog-card-header">
            <div>
              <h2>Kam qolgan tovarlar (1 tugmada avto-buyurtma)</h2>
              <p>Kassa sotuv tezligi asosida hisoblangan tavsiya miqdorlar</p>
            </div>
          </div>
          <div class="clean-table">
            ${options.autoRestock
              .map(
                (item) => `
              <div class="table-row">
                <div class="cell-product">
                  <span class="status-badge red"><i class="dot red"></i> Qoldiq: ${Number(item.current_pos_qty)} dona</span>
                  <strong>${escapeHtml(item.product_name)}</strong>
                </div>
                <div class="tabular-nums">Tavsiya: <strong>${Number(item.recommended_order_qty)} dona</strong></div>
                <div></div>
                <div class="cell-actions">
                  <button type="button" class="btn-primary-cta" style="min-height:${designTokens.spacing.minTouchTargetMobilePx}px">1 tugmada buyurtma</button>
                </div>
              </div>`
              )
              .join("")}
          </div>
        </section>`
            : ""
        }
        ${drawerHtml}
      </main>
    </div>
  `;

  assertZeroJargonInText(html.replace(/<[^>]+>/g, " "));
  return html;
}
