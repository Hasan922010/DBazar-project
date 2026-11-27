/**
 * DBazar Redesigned Interactive UI Preview Server (`http://127.0.0.1:3000`)
 * Crafted with `agency-ux-architect`, `agency-ui-designer`, and `agency-frontend-developer`.
 * Provides full client-side interactivity for:
 * - Light / Dark / System Theme Toggle (`ThemeManager`)
 * - Web-Portal (Manufacturer, Intermediary, Buyer) + interactive "Batafsil" Drawer & 1-Click Cart
 * - Offline-First POS Workstation (Product tiles, F12 Fiscal QR Receipt Modal, F4 1-Click QR Kirim)
 * - Mobile App (4 Bottom Tabs, Buyer "+" Cart, Driver 1-Button "Ombordan oldim" -> "Yo'lga chiqdim" -> "Topshirdim")
 */
import fs from "node:fs";
import http from "node:http";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { WebPortalStore, renderCabinetHtml } from "./index.js";
import { OfflinePosDatabase, renderPosScreenHtml } from "../../pos-client/src/index.js";
import { MobileAppController, renderMobileScreenHtml } from "../../mobile-app/src/index.js";
import { SAMPLE_OFFER } from "../../../packages/shared-utils/src/index.js";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const cssPath = path.join(__dirname, "../../../packages/ui-tokens/design-system.css");
const baseCss = fs.readFileSync(cssPath, "utf-8");

const CATALOG_OFFERS = [
  SAMPLE_OFFER,
  {
    id: "22222222-1111-1111-1111-111111111111",
    seller_id: "22222222-2222-2222-2222-222222222222",
    seller_name: "Tashkent Agro Distribyutor",
    base_price_tiyin: 22_000_000,
    min_order_qty: 2,
    price_tiers: [{ min_qty: 10, max_qty: null, unit_price_tiyin: 21_000_000 }],
    variant: {
      id: "33333333-4444-4444-4444-444444444444",
      product_id: "44444444-5555-5555-5555-555555555555",
      product_name: "Birinchi navli bug'doy uni",
      brand: "Don",
      sku: "UN-50KG",
      variant_name: "50 kg qop",
      mxik_code: "01101002001000002",
      barcode: "4780020020022",
      unit_type: "KG",
      packaging_coefficient: 1,
      weight_grams: 50000,
    },
  },
  {
    id: "33333333-1111-1111-1111-111111111111",
    seller_id: "22222222-2222-2222-2222-222222222222",
    seller_name: "Xorazm Shakar Zavodi",
    base_price_tiyin: 32_500_000,
    min_order_qty: 5,
    price_tiers: [{ min_qty: 20, max_qty: null, unit_price_tiyin: 31_000_000 }],
    variant: {
      id: "33333333-6666-6666-6666-666666666666",
      product_id: "44444444-7777-7777-7777-777777777777",
      product_name: "Oq Kristall Shakar",
      brand: "Xorazm",
      sku: "SHAKAR-25KG",
      variant_name: "25 kg qop",
      mxik_code: "01701001001000003",
      barcode: "4780030030033",
      unit_type: "KG",
      packaging_coefficient: 1,
      weight_grams: 25000,
    },
  },
];

const port = Number(process.env.PORT || 3000);
const backendPort = Number(process.env.BACKEND_PORT || 8001);

function buildPage(urlObj) {
  const appMode = urlObj.searchParams.get("app") || "web";
  const role = urlObj.searchParams.get("role") || "MANUFACTURER";
  const drawerOpen = urlObj.searchParams.get("drawer") === "1";
  const offline = urlObj.searchParams.get("offline") === "1";

  let viewHtml = "";
  if (appMode === "pos") {
    const pos = new OfflinePosDatabase({
      storeId: "eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee",
      terminalId: "TERM-BARAKA-01",
      storeName: "Baraka Minimarket Kassa #1",
    });
    pos.isOnline = !offline;
    viewHtml = renderPosScreenHtml(pos, 18_500_000);
  } else if (appMode === "mobile") {
    const mob = new MobileAppController(role === "DRIVER" ? "DRIVER" : "BUYER_OR_AGENT");
    if (role === "DRIVER") {
      mob.activeDelivery = {
        shipmentId: "99999999-9999-9999-9999-999999999999",
        subOrderId: "88888888-8888-8888-8888-888888888888",
        customerName: "Baraka Minimarket #1",
        customerPhone: "+998904440044",
        address: "Toshkent sh., Chilonzor-9, 14-uy",
        status: "ASSIGNED",
        latMicrodeg: 41311081,
        lngMicrodeg: 69240562,
      };
    } else {
      mob.tapAddProduct(SAMPLE_OFFER, 50);
    }
    viewHtml = renderMobileScreenHtml(mob);
  } else {
    const store = new WebPortalStore(role);
    store.addToCartOneClick(SAMPLE_OFFER, 10);
    if (drawerOpen) store.openDetailsDrawer(SAMPLE_OFFER, "BATCH-OIL-2026-11");
    viewHtml = renderCabinetHtml(store, {
      vmi: {
        total_store_stock_qty: 625,
        total_sold_qty: 248,
        low_stock_alert_count: 2,
        items: [],
      },
      offers: CATALOG_OFFERS,
      autoRestock: [
        {
          product_name: "Birinchi navli bug'doy uni (50 kg qop)",
          current_pos_qty: 4,
          recommended_order_qty: 20,
        },
      ],
    });
  }

  const activeKey = `${appMode}:${role}:${drawerOpen ? "1" : "0"}:${offline ? "1" : "0"}`;

  return `<!DOCTYPE html>
<html lang="uz">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>DBazar — Minimalistik B2B & Cloud POS</title>
  <style>
    ${baseCss}

    /* Top Workspace Navigation Bar */
    .preview-switcher {
      display: flex;
      gap: 8px;
      padding: 10px 20px;
      background: #0F172A;
      color: #F8FAFC;
      flex-wrap: wrap;
      align-items: center;
      border-bottom: 1px solid #1E293B;
      position: sticky;
      top: 0;
      z-index: 100;
    }
    .preview-brand {
      display: flex;
      align-items: center;
      gap: 8px;
      font-weight: 700;
      font-size: 0.9rem;
      margin-right: 8px;
      color: #60A5FA;
    }
    .preview-switcher a {
      color: #CBD5E1;
      text-decoration: none;
      padding: 7px 13px;
      border-radius: 9999px;
      background: #1E293B;
      font-size: 0.82rem;
      font-weight: 600;
      border: 1px solid #334155;
      transition: all 150ms ease;
    }
    .preview-switcher a:hover,
    .preview-switcher a.active {
      background: #2563EB;
      color: #FFFFFF;
      border-color: #3B82F6;
    }
    .preview-api-links {
      margin-left: auto;
      display: flex;
      gap: 6px;
    }
    .preview-api-links a {
      background: rgba(16, 185, 129, 0.14);
      color: #34D399;
      border-color: rgba(16, 185, 129, 0.3);
    }

    /* Web-Portal Layout */
    .web-portal-layout {
      display: grid;
      grid-template-columns: 260px 1fr;
      min-height: calc(100vh - 54px);
      background-color: var(--bg-surface);
    }
    .sidebar {
      background-color: var(--bg-primary);
      border-right: 1px solid var(--border-subtle);
      padding: 24px 18px;
      display: flex;
      flex-direction: column;
      gap: 18px;
    }
    .brand-lockup {
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 4px 8px;
    }
    .brand-logo {
      width: 40px;
      height: 40px;
      border-radius: 10px;
      background: linear-gradient(135deg, #2563EB, #1D4ED8);
      color: #FFFFFF;
      font-weight: 800;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 1rem;
      box-shadow: var(--shadow-sm);
    }
    .brand-lockup strong {
      display: block;
      font-size: 1.05rem;
      line-height: 1.2;
    }
    .brand-lockup span {
      font-size: 0.78rem;
      color: var(--text-muted);
    }
    .role-chip {
      background-color: var(--brand-primary-soft);
      color: var(--brand-primary);
      padding: 8px 12px;
      border-radius: var(--radius-md);
      font-size: 0.8rem;
      font-weight: 700;
      border: 1px solid rgba(37, 99, 235, 0.2);
    }
    .sidebar ul {
      list-style: none;
      padding: 0;
      margin: 0;
      display: flex;
      flex-direction: column;
      gap: 6px;
    }
    .sidebar li {
      padding: 12px 14px;
      border-radius: var(--radius-md);
      font-weight: 600;
      font-size: 0.92rem;
      color: var(--text-secondary);
      cursor: pointer;
      transition: all var(--transition-fast);
    }
    .sidebar li:hover {
      background-color: var(--bg-subtle);
      color: var(--text-primary);
    }
    .sidebar li.active {
      background-color: var(--brand-primary);
      color: #FFFFFF;
      box-shadow: var(--shadow-xs);
    }
    .sidebar-footer {
      margin-top: auto;
      padding-top: 16px;
      border-top: 1px solid var(--border-subtle);
    }

    /* Main Content Area */
    .content {
      padding: 28px 36px;
      max-width: 1320px;
      width: 100%;
    }
    .topbar {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      gap: 20px;
      margin-bottom: 28px;
      flex-wrap: wrap;
    }
    .topbar-titles h1 {
      margin: 0 0 4px 0;
      font-size: 1.6rem;
      font-weight: 800;
      letter-spacing: -0.02em;
    }
    .topbar-titles p {
      margin: 0;
      color: var(--text-secondary);
      font-size: 0.92rem;
    }
    .topbar-controls {
      display: flex;
      align-items: center;
      gap: 14px;
    }

    /* 3 Traffic-Light KPI Cards */
    .kpi-grid {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 20px;
      margin-bottom: 28px;
    }
    .kpi-card {
      background-color: var(--bg-primary);
      border: 1px solid var(--border-subtle);
      border-radius: var(--radius-lg);
      padding: 22px 24px;
      display: flex;
      flex-direction: column;
      gap: 10px;
      box-shadow: var(--shadow-xs);
      transition: transform var(--transition-fast), box-shadow var(--transition-fast);
    }
    .kpi-card:hover {
      transform: translateY(-2px);
      box-shadow: var(--shadow-md);
    }
    .kpi-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      font-size: 0.9rem;
      font-weight: 600;
      color: var(--text-secondary);
    }
    .kpi-card strong {
      font-size: 2rem;
      font-weight: 800;
      line-height: 1.1;
    }
    .kpi-caption {
      font-size: 0.8rem;
      color: var(--text-muted);
    }
    .kpi-card[data-status="GREEN"] { border-top: 4px solid var(--status-ready); }
    .kpi-card[data-status="YELLOW"] { border-top: 4px solid var(--status-pending); }
    .kpi-card[data-status="RED"] { border-top: 4px solid var(--status-alert); }

    /* Clean Catalog Table Card */
    .catalog-card {
      background-color: var(--bg-primary);
      border: 1px solid var(--border-subtle);
      border-radius: var(--radius-lg);
      box-shadow: var(--shadow-sm);
      overflow: hidden;
    }
    .catalog-card-header {
      padding: 20px 24px;
      border-bottom: 1px solid var(--border-subtle);
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 12px;
    }
    .catalog-card-header h2 {
      margin: 0 0 2px 0;
      font-size: 1.15rem;
    }
    .catalog-card-header p {
      margin: 0;
      font-size: 0.85rem;
      color: var(--text-muted);
    }
    .cart-pill {
      background-color: var(--brand-primary-soft);
      color: var(--brand-primary);
      padding: 10px 16px;
      border-radius: var(--radius-md);
      font-size: 0.92rem;
      border: 1px solid rgba(37, 99, 235, 0.2);
    }
    .table-row {
      display: grid;
      grid-template-columns: 2.2fr 1.3fr 1.2fr auto;
      align-items: center;
      padding: 18px 24px;
      border-bottom: 1px solid var(--border-subtle);
      gap: 16px;
      transition: background-color var(--transition-fast);
    }
    .table-row:last-child { border-bottom: none; }
    .table-row:hover { background-color: var(--bg-surface); }
    .cell-product {
      display: flex;
      align-items: center;
      gap: 14px;
    }
    .product-avatar {
      width: 44px;
      height: 44px;
      border-radius: 12px;
      background-color: var(--brand-primary-soft);
      color: var(--brand-primary);
      font-weight: 800;
      font-size: 1.1rem;
      display: flex;
      align-items: center;
      justify-content: center;
      flex-shrink: 0;
    }
    .product-title {
      font-weight: 700;
      font-size: 0.98rem;
      margin-bottom: 2px;
    }
    .product-meta {
      font-size: 0.8rem;
      color: var(--text-muted);
    }
    .cell-seller {
      display: flex;
      flex-direction: column;
      align-items: flex-start;
      gap: 4px;
    }
    .seller-name {
      font-weight: 600;
      font-size: 0.92rem;
    }
    .base-price {
      font-weight: 800;
      font-size: 1.05rem;
    }
    .tier-pill {
      display: inline-block;
      margin-top: 4px;
      font-size: 0.76rem;
      font-weight: 600;
      padding: 2px 8px;
      border-radius: 6px;
      background-color: var(--status-ready-bg);
      color: var(--status-ready-text);
    }
    .cell-actions {
      display: flex;
      gap: 10px;
    }

    /* Progressive Disclosure Side Drawer */
    .side-drawer {
      position: fixed;
      top: 54px;
      right: 0;
      width: 400px;
      bottom: 0;
      background-color: var(--bg-primary);
      border-left: 1px solid var(--border-strong);
      padding: 28px 24px;
      box-shadow: var(--shadow-lg);
      z-index: 90;
      display: flex;
      flex-direction: column;
      gap: 20px;
    }
    .drawer-header {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      gap: 12px;
      padding-bottom: 16px;
      border-bottom: 1px solid var(--border-subtle);
    }
    .drawer-eyebrow {
      font-size: 0.75rem;
      text-transform: uppercase;
      letter-spacing: 0.06em;
      color: var(--brand-primary);
      font-weight: 700;
    }
    .drawer-header h3 {
      margin: 4px 0 0 0;
      font-size: 1.2rem;
    }
    .drawer-grid {
      display: flex;
      flex-direction: column;
      gap: 12px;
    }
    .drawer-item {
      padding: 14px 16px;
      border-radius: var(--radius-md);
      background-color: var(--bg-surface);
      border: 1px solid var(--border-subtle);
      display: flex;
      flex-direction: column;
      gap: 4px;
    }
    .drawer-item span {
      font-size: 0.8rem;
      color: var(--text-muted);
    }
    .drawer-item strong {
      font-size: 1rem;
    }

    /* Offline-First POS Workstation Layout */
    .pos-split-layout {
      padding: 20px 28px;
      max-width: 1380px;
      margin: 0 auto;
    }
    .pos-topbar {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 20px;
      padding: 16px 22px;
      background-color: var(--bg-primary);
      border: 1px solid var(--border-subtle);
      border-radius: var(--radius-lg);
      box-shadow: var(--shadow-xs);
      gap: 16px;
      flex-wrap: wrap;
    }
    .pos-store-info h1 {
      margin: 0;
      font-size: 1.35rem;
      font-weight: 800;
    }
    .pos-terminal-tag {
      font-size: 0.82rem;
      color: var(--text-muted);
    }
    .pos-columns {
      display: grid;
      grid-template-columns: 1.45fr 1fr;
      gap: 24px;
      align-items: start;
    }
    .pos-left-catalog, .pos-right-receipt {
      background-color: var(--bg-primary);
      border: 1px solid var(--border-subtle);
      border-radius: var(--radius-lg);
      padding: 22px;
      box-shadow: var(--shadow-sm);
      display: flex;
      flex-direction: column;
      gap: 18px;
    }
    .pos-tiles-grid {
      display: grid;
      grid-template-columns: repeat(2, 1fr);
      gap: 14px;
    }
    .pos-product-tile {
      display: flex;
      flex-direction: column;
      align-items: flex-start;
      text-align: left;
      padding: 18px;
      min-height: 132px;
      background-color: var(--bg-surface);
      border: 1.5px solid var(--border-subtle);
      border-radius: var(--radius-lg);
      gap: 8px;
    }
    .pos-product-tile:hover {
      border-color: var(--brand-primary);
      background-color: var(--brand-primary-soft);
      transform: translateY(-2px);
      box-shadow: var(--shadow-sm);
    }
    .tile-category {
      font-size: 0.75rem;
      font-weight: 700;
      text-transform: uppercase;
      color: var(--text-muted);
    }
    .pos-product-tile strong {
      font-size: 1.02rem;
      color: var(--text-primary);
    }
    .tile-price {
      font-size: 1.15rem;
      font-weight: 800;
      color: var(--brand-primary);
    }
    .receipt-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding-bottom: 12px;
      border-bottom: 1px solid var(--border-subtle);
    }
    .receipt-lines {
      display: flex;
      flex-direction: column;
      gap: 10px;
      min-height: 180px;
    }
    .receipt-line {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 12px 14px;
      background-color: var(--bg-surface);
      border-radius: var(--radius-md);
      border: 1px solid var(--border-subtle);
    }
    .receipt-line small {
      display: block;
      color: var(--text-muted);
      font-size: 0.8rem;
    }
    .pos-payment-modes {
      display: grid;
      grid-template-columns: repeat(2, 1fr);
      gap: 8px;
    }
    .pay-mode {
      min-height: 44px;
      background-color: var(--bg-surface);
      border: 1px solid var(--border-strong);
      color: var(--text-secondary);
      font-size: 0.85rem;
    }
    .pay-mode.active {
      background-color: var(--brand-primary-soft);
      border-color: var(--brand-primary);
      color: var(--brand-primary);
    }
    .receipt-summary {
      display: flex;
      justify-content: space-between;
      align-items: baseline;
      padding-top: 12px;
      border-top: 2px dashed var(--border-strong);
    }
    .receipt-total {
      font-size: 2.1rem;
      font-weight: 900;
      color: var(--text-primary);
    }

    /* Mobile Device Frame */
    .mobile-shell {
      max-width: 412px;
      margin: 28px auto;
      border: 8px solid #1E293B;
      border-radius: 36px;
      overflow: hidden;
      background-color: var(--bg-primary);
      box-shadow: var(--shadow-lg);
    }
    .mobile-notch {
      width: 120px;
      height: 20px;
      background: #1E293B;
      margin: 0 auto;
      border-bottom-left-radius: 14px;
      border-bottom-right-radius: 14px;
    }
    .mobile-shell main {
      padding: 20px;
      min-height: 540px;
      display: flex;
      flex-direction: column;
    }
    .buyer-screen, .driver-screen {
      display: flex;
      flex-direction: column;
      gap: 16px;
      flex: 1;
    }
    .mobile-header, .mobile-status-bar {
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 8px;
    }
    .mobile-product-list {
      display: flex;
      flex-direction: column;
      gap: 12px;
    }
    .mobile-product-card {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 16px;
      background-color: var(--bg-surface);
      border: 1px solid var(--border-subtle);
      border-radius: var(--radius-lg);
    }
    .mobile-product-card p {
      margin: 4px 0 0 0;
      font-size: 0.85rem;
      color: var(--brand-primary);
      font-weight: 700;
    }
    .mobile-plus-btn {
      font-size: 1.4rem;
      font-weight: 800;
      background-color: var(--brand-primary-soft);
      color: var(--brand-primary);
      border-color: var(--brand-primary);
    }
    .mobile-checkout-bar {
      margin-top: auto;
      padding: 16px;
      background-color: var(--bg-surface);
      border: 1px solid var(--border-subtle);
      border-radius: var(--radius-lg);
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    .cart-summary {
      font-size: 1.25rem;
      font-weight: 800;
    }
    .driver-map-card {
      height: 150px;
      border-radius: var(--radius-lg);
      background: linear-gradient(135deg, #DBEAFE 0%, #EFF6FF 100%);
      border: 1px solid #BFDBFE;
      position: relative;
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 0 24px;
      overflow: hidden;
    }
    [data-theme="dark"] .driver-map-card {
      background: linear-gradient(135deg, #1E3A8A 0%, #172554 100%);
      border-color: #1D4ED8;
    }
    .map-route-line {
      position: absolute;
      left: 50px;
      right: 50px;
      height: 4px;
      background: repeating-linear-gradient(90deg, #2563EB 0, #2563EB 10px, transparent 10px, transparent 18px);
    }
    .map-pin {
      position: relative;
      z-index: 2;
      padding: 6px 12px;
      border-radius: var(--radius-pill);
      background: var(--bg-primary);
      font-size: 0.78rem;
      font-weight: 700;
      box-shadow: var(--shadow-sm);
    }
    .driver-customer-card {
      padding: 18px;
      background-color: var(--bg-surface);
      border: 1px solid var(--border-subtle);
      border-radius: var(--radius-lg);
      display: flex;
      flex-direction: column;
      gap: 8px;
    }
    .driver-customer-card h2 {
      margin: 0;
      font-size: 1.2rem;
    }
    .driver-customer-card p {
      margin: 0 0 8px 0;
      color: var(--text-secondary);
      font-size: 0.9rem;
    }
    .driver-pod-box {
      padding: 14px;
      background-color: var(--bg-surface);
      border: 1px solid var(--border-subtle);
      border-radius: var(--radius-md);
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 12px;
    }
    .driver-pod-box label {
      font-size: 0.82rem;
      font-weight: 600;
      color: var(--text-secondary);
    }
    .driver-pod-box input {
      width: 110px;
      min-height: 42px;
      text-align: center;
      font-size: 1.1rem;
      font-weight: 800;
      border: 1.5px solid var(--brand-primary);
      border-radius: var(--radius-sm);
      background: var(--bg-primary);
      color: var(--text-primary);
    }
    .driver-main-cta {
      margin-top: auto;
      width: 100%;
      font-size: 1.15rem;
    }
    .bottom-tab-bar {
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      border-top: 1px solid var(--border-subtle);
      background-color: var(--bg-surface);
      padding: 4px;
      gap: 4px;
    }
    .bottom-tab {
      background: transparent;
      border: none;
      color: var(--text-muted);
      font-size: 0.78rem;
      font-weight: 700;
      border-radius: var(--radius-sm);
    }
    .bottom-tab.active {
      background-color: var(--brand-primary-soft);
      color: var(--brand-primary);
    }

    input[type="search"] {
      width: 100%;
      min-height: 48px;
      padding: 0 16px;
      border: 1.5px solid var(--border-strong);
      border-radius: var(--radius-md);
      font-size: 0.95rem;
      background-color: var(--bg-primary);
      color: var(--text-primary);
    }

    /* Toast Feedback */
    #dbazar-toast {
      position: fixed;
      bottom: 24px;
      right: 24px;
      background: #0F172A;
      color: #FFFFFF;
      padding: 14px 20px;
      border-radius: var(--radius-md);
      font-weight: 600;
      font-size: 0.9rem;
      box-shadow: var(--shadow-lg);
      border-left: 4px solid #16A34A;
      opacity: 0;
      pointer-events: none;
      transform: translateY(12px);
      transition: all 200ms ease;
      z-index: 200;
    }
    #dbazar-toast.visible {
      opacity: 1;
      transform: translateY(0);
    }

    @media (max-width: 960px) {
      .web-portal-layout, .pos-columns, .kpi-grid {
        grid-template-columns: 1fr;
      }
      .table-row {
        grid-template-columns: 1fr;
      }
    }
  </style>
</head>
<body>
  <div class="preview-switcher">
    <div class="preview-brand">◆ DBazar UI Tizimi</div>
    <a href="/?app=web&role=MANUFACTURER" class="${activeKey.startsWith("web:MANUFACTURER") ? "active" : ""}">1. Ishlab chiqaruvchi</a>
    <a href="/?app=web&role=INTERMEDIARY" class="${activeKey.startsWith("web:INTERMEDIARY") ? "active" : ""}">2. Distribyutor</a>
    <a href="/?app=web&role=CUSTOMER" class="${activeKey === "web:CUSTOMER:0:0" ? "active" : ""}">3. Xaridor Portali</a>
    <a href="/?app=web&role=CUSTOMER&drawer=1" class="${activeKey === "web:CUSTOMER:1:0" ? "active" : ""}">3b. Soliq & Partiya Drawer</a>
    <a href="/?app=pos" class="${activeKey === "pos:MANUFACTURER:0:0" ? "active" : ""}">4. POS Kassa (Onlayn)</a>
    <a href="/?app=pos&offline=1" class="${activeKey === "pos:MANUFACTURER:0:1" ? "active" : ""}">4b. POS Kassa (Oflayn)</a>
    <a href="/?app=mobile&role=BUYER" class="${activeKey.startsWith("mobile:BUYER") ? "active" : ""}">5. Mobil (Xaridor)</a>
    <a href="/?app=mobile&role=DRIVER" class="${activeKey.startsWith("mobile:DRIVER") ? "active" : ""}">6. Mobil (Haydovchi POD)</a>
    <div class="preview-api-links">
      <a href="http://127.0.0.1:${backendPort}/api/v1/openapi.json" target="_blank">OpenAPI 3.1</a>
      <a href="http://127.0.0.1:${backendPort}/healthz/" target="_blank">Healthz</a>
      <a href="http://127.0.0.1:${backendPort}/admin/" target="_blank">Admin</a>
    </div>
  </div>
  ${viewHtml}
  <div id="dbazar-toast" role="status" aria-live="polite"></div>

  <script>
    (function () {
      const toastEl = document.getElementById("dbazar-toast");
      function showToast(msg) {
        if (!toastEl) return;
        toastEl.textContent = msg;
        toastEl.classList.add("visible");
        clearTimeout(window.__toastTimer);
        window.__toastTimer = setTimeout(() => toastEl.classList.remove("visible"), 2800);
      }

      function formatSom(tiyin) {
        const som = Math.round(tiyin / 100);
        return som.toString().replace(/\\B(?=(\\d{3})+(?!\\d))/g, " ") + " so'm";
      }

      // 1. Theme Switcher (Light / Dark / System)
      const rootLayout = document.querySelector(".web-portal-layout") || document.documentElement;
      const savedTheme = localStorage.getItem("dbazar-theme");
      if (savedTheme === "dark" || savedTheme === "light") {
        document.documentElement.setAttribute("data-theme", savedTheme);
        if (rootLayout) rootLayout.setAttribute("data-theme", savedTheme);
      }

      document.querySelectorAll(".theme-toggle button").forEach((btn) => {
        btn.addEventListener("click", () => {
          const mode = btn.getAttribute("data-theme") || "light";
          document.querySelectorAll(".theme-toggle button").forEach((b) => b.classList.remove("active"));
          btn.classList.add("active");
          const resolved =
            mode === "system"
              ? window.matchMedia("(prefers-color-scheme: dark)").matches
                ? "dark"
                : "light"
              : mode;
          document.documentElement.setAttribute("data-theme", resolved);
          if (rootLayout) rootLayout.setAttribute("data-theme", resolved);
          localStorage.setItem("dbazar-theme", resolved);
          showToast("Mavzu o'zgartirildi: " + btn.textContent);
        });
      });

      // 2. Web-Portal Interactive Cart & Drawer
      let portalCartTiyin = 18000000;
      document.querySelectorAll('[data-action="add-cart"]').forEach((btn) => {
        btn.addEventListener("click", () => {
          portalCartTiyin += 16500000;
          const totalEl = document.getElementById("portal-cart-total");
          if (totalEl) totalEl.textContent = formatSom(portalCartTiyin);
          showToast("Savatga qo'shildi · Ulgurji chegirma qo'llandi!");
        });
      });

      document.querySelectorAll('[data-action="drawer"]').forEach((btn) => {
        btn.addEventListener("click", () => {
          const url = new URL(window.location.href);
          url.searchParams.set("drawer", url.searchParams.get("drawer") === "1" ? "0" : "1");
          window.location.href = url.toString();
        });
      });

      const closeDrawerBtn = document.querySelector('[data-action="close-drawer"]');
      if (closeDrawerBtn) {
        closeDrawerBtn.addEventListener("click", () => {
          const url = new URL(window.location.href);
          url.searchParams.delete("drawer");
          window.location.href = url.toString();
        });
      }

      // 3. POS Workstation Interactive Tiles, F12 Pay & F4 QR Inbound
      let posTotalTiyin = 18500000;
      document.querySelectorAll('[data-action="pos-tile"]').forEach((tile) => {
        tile.addEventListener("click", () => {
          const price = Number(tile.getAttribute("data-price") || 1500000);
          const name = tile.getAttribute("data-name") || "Tovar";
          posTotalTiyin += price;
          const totalEl = document.getElementById("pos-total-display");
          if (totalEl) totalEl.textContent = formatSom(posTotalTiyin);
          const linesEl = document.getElementById("pos-receipt-lines");
          if (linesEl) {
            const div = document.createElement("div");
            div.className = "receipt-line";
            div.innerHTML =
              "<div><strong>" +
              name +
              '</strong><small class="tabular-nums">1 dona × ' +
              formatSom(price) +
              '</small></div><strong class="tabular-nums">' +
              formatSom(price) +
              "</strong>";
            linesEl.appendChild(div);
          }
          showToast(name + " chekka qo'shildi");
        });
      });

      const posPayBtn = document.querySelector('[data-action="pos-pay"]');
      function triggerPosPay() {
        showToast("Soliq.uz Fiskal QR-chek chop etildi! Jami: " + formatSom(posTotalTiyin));
      }
      if (posPayBtn) posPayBtn.addEventListener("click", triggerPosPay);

      const posQrBtn = document.querySelector('[data-action="pos-qr-inbound"]');
      if (posQrBtn) {
        posQrBtn.addEventListener("click", () => {
          showToast("1 tugmada kirim bajarildi: Yuk xatidagi barcha tovarlar va 17 xonali kodlar bazaga tushdi!");
        });
      }

      window.addEventListener("keydown", (e) => {
        if (e.key === "F12" && posPayBtn) {
          e.preventDefault();
          triggerPosPay();
        }
      });

      // 4. Mobile Buyer "+" & Driver 1-Button Status Cycling
      let mobileCartTiyin = 82500000;
      document.querySelectorAll('[data-action="mobile-add"]').forEach((btn) => {
        btn.addEventListener("click", () => {
          const price = Number(btn.getAttribute("data-price") || 1650000);
          mobileCartTiyin += price * 10;
          const el = document.getElementById("mobile-cart-total");
          if (el) el.textContent = formatSom(mobileCartTiyin);
          showToast("Savatga +10 dona qo'shildi");
        });
      });

      const driverSteps = ["Ombordan oldim", "Yo'lga chiqdim", "Topshirdim", "Yetkazildi ✓ (To'lov o'tkazildi)"];
      let driverStepIdx = 0;
      const driverBtn = document.querySelector('[data-action="driver-step"]');
      if (driverBtn) {
        driverBtn.addEventListener("click", () => {
          driverStepIdx = Math.min(driverSteps.length - 1, driverStepIdx + 1);
          driverBtn.textContent = driverSteps[driverStepIdx];
          showToast("Haydovchi holati yangilandi: " + driverSteps[driverStepIdx]);
        });
      }
    })();
  </script>
</body>
</html>`;
}

const server = http.createServer((req, res) => {
  const urlObj = new URL(req.url || "/", `http://127.0.0.1:${port}`);
  if (urlObj.pathname.startsWith("/api/v1/") || urlObj.pathname === "/healthz/") {
    const proxyReq = http.request(
      {
        hostname: "127.0.0.1",
        port: backendPort,
        path: urlObj.pathname + urlObj.search,
        method: req.method,
        headers: req.headers,
      },
      (proxyRes) => {
        res.writeHead(proxyRes.statusCode || 200, proxyRes.headers);
        proxyRes.pipe(res);
      }
    );
    proxyReq.on("error", () => {
      res.writeHead(502, { "Content-Type": "application/json" });
      res.end(JSON.stringify({ error_code: "BACKEND_UNAVAILABLE", message: "Backend server ishlamayapti." }));
    });
    req.pipe(proxyReq);
    return;
  }
  res.writeHead(200, { "Content-Type": "text/html; charset=utf-8" });
  res.end(buildPage(urlObj));
});

server.listen(port, "0.0.0.0", () => {
  console.log(`DBazar Frontend Preview Server running at http://127.0.0.1:${port}`);
});
