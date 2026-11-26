/**
 * `@dbazar/shared-utils`
 * Provides deterministic cross-platform utilities for Web, POS (Electron/SQLite), and React Native:
 * 1. Hybrid Logical Clock (HLC) generator, parser & monotonic comparator (`<wall_ms>:<counter>:<node_id>`)
 * 2. Tiyin integer formatting (`tabular-nums` ready, zero floating-point drift)
 * 3. 17-digit MXIK and 9-digit STIR (INN) validators
 * 4. Tiered pricing calculator in integer tiyin
 */

const MXIK_REGEX = /^\d{17}$/;
const STIR_REGEX = /^\d{9}$/;
const HLC_REGEX = /^(\d{10,16}):(\d{1,8}):([A-Za-z0-9_-]{1,64})$/;

export function isValidMxikCode(mxikCode) {
  return MXIK_REGEX.test(mxikCode || "");
}

export function isValidStirInn(stir) {
  return STIR_REGEX.test(stir || "");
}

export function parseHlcTimestamp(hlc) {
  const match = HLC_REGEX.exec(hlc || "");
  if (!match) {
    throw new Error(`Noto'g'ri HLC formati: '${hlc}'. Kutilgan: '<wall_ms>:<counter>:<node_id>'`);
  }
  return {
    wallTimeMs: Number(match[1]),
    logicalCounter: Number(match[2]),
    nodeId: match[3],
  };
}

export function compareHlcTimestamps(a, b) {
  const pa = parseHlcTimestamp(a);
  const pb = parseHlcTimestamp(b);
  if (pa.wallTimeMs !== pb.wallTimeMs) return pa.wallTimeMs - pb.wallTimeMs;
  if (pa.logicalCounter !== pb.logicalCounter) return pa.logicalCounter - pb.logicalCounter;
  return pa.nodeId.localeCompare(pb.nodeId);
}

export function generateHlcTimestamp(nodeId, lastHlc = null, nowMs = Date.now()) {
  const physicalMs = Math.trunc(nowMs);
  if (!lastHlc) {
    return `${physicalMs}:0:${nodeId}`;
  }
  const prev = parseHlcTimestamp(lastHlc);
  if (physicalMs > prev.wallTimeMs) {
    return `${physicalMs}:0:${nodeId}`;
  }
  return `${prev.wallTimeMs}:${prev.logicalCounter + 1}:${nodeId}`;
}

export function formatTiyinUzs(amountTiyin) {
  if (!Number.isInteger(amountTiyin)) {
    throw new Error(`Moliyaviy xato: Summa butun tiyin bo'lishi shart, kelgan qiymat: ${amountTiyin}`);
  }
  const sign = amountTiyin < 0 ? "-" : "";
  const absTiyin = Math.abs(amountTiyin);
  const som = Math.trunc(absTiyin / 100);
  const tiyin = absTiyin % 100;
  const formattedSom = som.toString().replace(/\B(?=(\d{3})+(?!\d))/g, " ");
  if (tiyin === 0) {
    return `${sign}${formattedSom} so'm`;
  }
  return `${sign}${formattedSom}.${tiyin.toString().padStart(2, "0")} so'm`;
}

export function calculateTieredPriceTiyin(basePriceTiyin, tiers, quantity) {
  if (!Number.isInteger(basePriceTiyin) || basePriceTiyin <= 0) {
    throw new Error("Bazaviy narx musbat butun tiyin bo'lishi shart.");
  }
  if (!Number.isInteger(quantity) || quantity <= 0) {
    throw new Error("Miqdor musbat butun son bo'lishi shart.");
  }
  let unitPriceTiyin = basePriceTiyin;
  const sorted = [...(tiers || [])].sort((a, b) => a.min_qty - b.min_qty);
  for (const tier of sorted) {
    if (quantity >= tier.min_qty && (tier.max_qty == null || quantity <= tier.max_qty)) {
      unitPriceTiyin = tier.unit_price_tiyin;
    }
  }
  return {
    unitPriceTiyin,
    totalPriceTiyin: unitPriceTiyin * quantity,
  };
}
