/**
 * POS Hardware Simulator (`@dbazar/pos-hardware-sim`)
 */
import { formatTiyinUzs, isValidMxikCode } from "../../../shared-utils/src/index.js";

export function printEscPosReceipt(storeName, items, totalTiyin, fiscalQrUrl) {
  for (const item of items) {
    if (!isValidMxikCode(item.mxikCode)) {
      throw new Error(`Chekda noto'g'ri 17 xonali MXIK kodi: ${item.mxikCode}`);
    }
  }
  const lines = [
    `=== ${storeName} ===`,
    "--------------------------------",
    ...items.flatMap((it) => [
      `${it.name} x${it.qty}  ${formatTiyinUzs(it.lineTotalTiyin)}`,
      `  MXIK: ${it.mxikCode}`,
    ]),
    "--------------------------------",
    `JAMI: ${formatTiyinUzs(totalTiyin)}`,
    `FISKAL QR: ${fiscalQrUrl}`,
  ];
  const textPreview = lines.join("\n");
  const encoder = new TextEncoder();
  const body = encoder.encode(textPreview);
  const rawBytes = new Uint8Array(2 + body.length + 4);
  rawBytes.set([0x1b, 0x40], 0);
  rawBytes.set(body, 2);
  rawBytes.set([0x0a, 0x1d, 0x56, 0x01], 2 + body.length);

  return { textPreview, rawBytes, fiscalQrUrl };
}

export function readCasScaleWeightGrams(pluCode, simulatedGrams = 1250) {
  if (simulatedGrams <= 0) {
    throw new Error("Tarozi vazni 0 grammdan katta bo'lishi kerak.");
  }
  return { pluCode, weightGrams: simulatedGrams, stable: true };
}
