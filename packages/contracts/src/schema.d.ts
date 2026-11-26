// AUTO-GENERATED FROM packages/contracts/openapi.yaml (Django 5 -> TypeScript Contract-First)
// Do not edit manually. Run `node packages/contracts/generate.js`.

export interface ErrorResponseSchema {
  error_code: string;
  message: string;
  correlation_id: string;
  details?: Record<string, unknown> | null;
}

export interface RegisterOrganizationRequest {
  username: string;
  password: string;
  phone: string;
  org_name: string;
  legal_name: string;
  stir_inn: string;
  role: "MANUFACTURER" | "INTERMEDIARY" | "LOGISTICS" | "CUSTOMER" | "ADMIN";
  region?: string;
  address?: string;
}

export interface OrganizationResponse {
  id: string;
  name: string;
  legal_name: string;
  stir_inn: string;
  role: string;
  kyb_status: string;
  eimzo_cert_serial: string;
  region: string;
}

export interface UserProfileResponse {
  id: string;
  username: string;
  phone: string;
  role: string;
  is_2fa_enabled: boolean;
  organization?: OrganizationResponse | null;
}

export interface AuthTokenResponse {
  access_token: string;
  token_type?: string;
  user: UserProfileResponse;
}

export interface LoginRequest {
  username: string;
  password: string;
}

export interface KybVerifyRequest {
  pkcs7_signature: string;
}

export interface CreateProductVariantRequest {
  name: string;
  brand?: string;
  description?: string;
  sku: string;
  variant_name: string;
  mxik_code: string;
  barcode: string;
  unit_type?: "PCS" | "BOX" | "KG" | "LITER";
  packaging_coefficient?: number;
  weight_grams?: number;
  category_slug?: string | null;
}

export interface ProductVariantResponse {
  id: string;
  product_id: string;
  product_name: string;
  brand: string;
  sku: string;
  variant_name: string;
  mxik_code: string;
  barcode: string;
  unit_type: string;
  packaging_coefficient: number;
  weight_grams: number;
}

export interface PriceTierInput {
  min_qty: number;
  max_qty?: number | null;
  unit_price_tiyin: number;
}

export interface UpsertOfferRequest {
  variant_id: string;
  base_price_tiyin: number;
  min_order_qty?: number;
  tiers?: PriceTierInput[];
}

export interface PriceTierResponse {
  min_qty: number;
  max_qty?: number | null;
  unit_price_tiyin: number;
}

export interface OfferResponse {
  id: string;
  seller_id: string;
  seller_name: string;
  variant: ProductVariantResponse;
  base_price_tiyin: number;
  min_order_qty: number;
  price_tiers: PriceTierResponse[];
}

export interface OfferListResponse {
  items: OfferResponse[];
}

export interface CalculatePriceRequest {
  quantity: number;
}

export interface CalculatePriceResponse {
  offer_id: string;
  quantity: number;
  unit_price_tiyin: number;
  total_price_tiyin: number;
}

export interface CreateWarehouseRequest {
  name: string;
  code: string;
  region?: string;
  address?: string;
}

export interface WarehouseResponse {
  id: string;
  organization_id: string;
  name: string;
  code: string;
  region: string;
  address: string;
}

export interface ReceiveStockRequest {
  warehouse_id: string;
  variant_id: string;
  batch_id: string;
  qty: number;
  expiry_date?: string | null;
  min_stock_threshold?: number;
}

export interface InventoryStockResponse {
  id: string;
  warehouse_id: string;
  warehouse_code: string;
  variant_id: string;
  sku: string;
  batch_id: string;
  available_qty: number;
  reserved_qty: number;
  min_stock_threshold: number;
  expiry_date?: string | null;
}

export interface TelemetryPermissionRequest {
  viewer_org_id: string;
  is_active?: boolean;
  variant_id?: string | null;
  batch_id?: string;
}

export interface TelemetryPermissionResponse {
  id: string;
  customer_org_id: string;
  viewer_org_id: string;
  variant_id?: string | null;
  batch_id: string;
  is_active: boolean;
}

export interface VmiLineageItemResponse {
  id: string;
  customer_org_id: string;
  customer_org_name: string;
  variant_id: string;
  sku: string;
  product_name: string;
  batch_id: string;
  supplied_qty: number;
  current_pos_qty: number;
  sold_pos_qty: number;
  min_restock_threshold: number;
  traffic_light_status: string;
}

export interface VmiTelemetryDashboardResponse {
  total_store_stock_qty: number;
  total_sold_qty: number;
  low_stock_alert_count: number;
  items: VmiLineageItemResponse[];
}

export interface OrderCartItemInput {
  offer_id: string;
  quantity: number;
}

export interface CreateOrderRequest {
  idempotency_key: string;
  is_preorder?: boolean;
  delivery_address?: string;
  items: OrderCartItemInput[];
}

export interface SubOrderItemResponse {
  id: string;
  variant_id: string;
  sku: string;
  product_name: string;
  mxik_code: string;
  barcode: string;
  batch_id: string;
  quantity: number;
  unit_price_tiyin: number;
  line_total_tiyin: number;
}

export interface SubOrderResponse {
  id: string;
  seller_org_id: string;
  seller_org_name: string;
  status: string;
  subtotal_amount_tiyin: number;
  waybill_qr_token: string;
  is_pos_inbounded: boolean;
  items: SubOrderItemResponse[];
}

export interface OrderResponse {
  id: string;
  buyer_org_id: string;
  status: string;
  is_preorder: boolean;
  total_amount_tiyin: number;
  delivery_address: string;
  idempotency_key: string;
  sub_orders: SubOrderResponse[];
}

export interface WalletTopupRequest {
  amount_tiyin: number;
  idempotency_key: string;
  provider?: "PAYME" | "CLICK" | "BANK_TRANSFER";
}

export interface LedgerAccountResponse {
  id: string;
  organization_id?: string | null;
  account_type: string;
  currency: string;
  balance_tiyin: number;
  credit_limit_tiyin: number;
  discount_tier_bps: number;
}

export interface EscrowHoldRequest {
  order_id: string;
  idempotency_key: string;
  payment_provider?: "PAYME" | "CLICK" | "BANK_TRANSFER" | "NASIYA";
}

export interface EscrowHoldResponse {
  id: string;
  order_id: string;
  sub_order_id: string;
  buyer_org_id: string;
  seller_org_id: string;
  amount_tiyin: number;
  seller_net_tiyin: number;
  platform_fee_tiyin: number;
  status: string;
  payment_provider: string;
}

export interface EscrowHoldListResponse {
  items: EscrowHoldResponse[];
}

export interface EscrowReleaseRequest {
  sub_order_id: string;
  idempotency_key: string;
}

export interface CreatePosStoreRequest {
  name: string;
  terminal_id: string;
  address?: string;
}

export interface PosStoreResponse {
  id: string;
  organization_id: string;
  name: string;
  terminal_id: string;
  address: string;
  last_hlc_timestamp: string;
}

export interface PosDeltaEventInput {
  client_event_id: string;
  variant_id: string;
  batch_id?: string;
  event_type: "INBOUND" | "SALE" | "RETURN" | "WRITE_OFF";
  quantity: number;
  unit_price_tiyin?: number;
  hlc_timestamp: string;
  waybill_qr_token?: string | null;
}

export interface PosDeltaSyncBatchRequest {
  store_id: string;
  events: PosDeltaEventInput[];
}

export interface PosDeltaSyncBatchResponse {
  store_id: string;
  applied_events: number;
  skipped_duplicates: number;
  conflicts: number;
  last_hlc_timestamp: string;
}

export interface OneClickWaybillInboundRequest {
  store_id: string;
  waybill_qr_token: string;
}

export interface OneClickWaybillInboundResponse {
  store_id: string;
  sub_order_id: string;
  waybill_qr_token: string;
  inbounded_items_count: number;
  total_waybill_items: number;
  is_pos_inbounded: boolean;
}

export interface GenerateDidoxEhfRequest {
  sub_order_id: string;
  pkcs7_signature: string;
}

export interface EhfDocumentResponse {
  id: string;
  sub_order_id: string;
  didox_doc_id: string;
  seller_stir: string;
  buyer_stir: string;
  total_amount_tiyin: number;
  certificate_serial: string;
  status: string;
}

export interface RegisterOfdReceiptRequest {
  store_id: string;
  client_sale_id: string;
  receipt_seq: number;
  payment_method?: "CASH" | "CARD" | "MIXED" | "NASIYA";
  total_amount_tiyin: number;
  mxik_codes: string[];
  hlc_timestamp: string;
}

export interface OfdFiscalReceiptResponse {
  id: string;
  pos_sale_id: string;
  terminal_id: string;
  receipt_seq: number;
  total_amount_tiyin: number;
  fiscal_sign: string;
  qr_code_url: string;
}

export interface DbazarConnectInboundRequest {
  external_system: "1C_ROZNITSA" | "BILLZ" | "REGOS" | "F_APTEKA";
  terminal_id: string;
  waybill_qr_token: string;
}

export interface DbazarConnectInboundResponse {
  external_system: string;
  terminal_id: string;
  store_id: string;
  sub_order_id: string;
  waybill_qr_token: string;
  inbounded_items_count: number;
  total_waybill_items: number;
  is_pos_inbounded: boolean;
}

export interface AssignShipmentRequest {
  sub_order_id: string;
}

export interface ShipmentResponse {
  id: string;
  sub_order_id: string;
  status: string;
  current_lat_microdeg: number;
  current_lng_microdeg: number;
  pod_photo_url: string;
}

export interface UpdateShipmentGpsRequest {
  lat_microdeg: number;
  lng_microdeg: number;
  status?: "PICKED_UP" | "IN_TRANSIT" | null;
}

export interface ConfirmPodRequest {
  pod_otp_code: string;
  release_idempotency_key: string;
  pod_photo_url?: string;
}

export interface ApiOperations {
  registerOrganizationAndUser: {
    method: "POST";
    path: "/api/v1/iam/register";
    request: RegisterOrganizationRequest;
    response: AuthTokenResponse;
  };
  loginUser: {
    method: "POST";
    path: "/api/v1/iam/login";
    request: LoginRequest;
    response: AuthTokenResponse;
  };
  verifyOrganizationKyb: {
    method: "POST";
    path: "/api/v1/iam/kyb/verify";
    request: KybVerifyRequest;
    response: OrganizationResponse;
  };
  getCurrentUserProfile: {
    method: "GET";
    path: "/api/v1/iam/me";
    request: void;
    response: UserProfileResponse;
  };
  createCatalogProductVariant: {
    method: "POST";
    path: "/api/v1/catalog/products";
    request: CreateProductVariantRequest;
    response: ProductVariantResponse;
  };
  upsertCatalogOffer: {
    method: "POST";
    path: "/api/v1/catalog/offers";
    request: UpsertOfferRequest;
    response: OfferResponse;
  };
  listCatalogOffers: {
    method: "GET";
    path: "/api/v1/catalog/offers";
    request: void;
    response: OfferListResponse;
  };
  calculateOfferTieredPrice: {
    method: "POST";
    path: "/api/v1/catalog/offers/{offer_id}/calculate-price";
    request: CalculatePriceRequest;
    response: CalculatePriceResponse;
  };
  createInventoryWarehouse: {
    method: "POST";
    path: "/api/v1/inventory/warehouses";
    request: CreateWarehouseRequest;
    response: WarehouseResponse;
  };
  receiveWarehouseStock: {
    method: "POST";
    path: "/api/v1/inventory/stocks/receive";
    request: ReceiveStockRequest;
    response: InventoryStockResponse;
  };
  setPosTelemetryPermission: {
    method: "POST";
    path: "/api/v1/inventory/vmi/permissions";
    request: TelemetryPermissionRequest;
    response: TelemetryPermissionResponse;
  };
  getVmiTelemetryDashboard: {
    method: "GET";
    path: "/api/v1/inventory/vmi/telemetry";
    request: void;
    response: VmiTelemetryDashboardResponse;
  };
  createB2BOrder: {
    method: "POST";
    path: "/api/v1/orders";
    request: CreateOrderRequest;
    response: OrderResponse;
  };
  getSubOrderWaybillByQr: {
    method: "GET";
    path: "/api/v1/orders/waybill/{waybill_qr_token}";
    request: void;
    response: SubOrderResponse;
  };
  topupBuyerWallet: {
    method: "POST";
    path: "/api/v1/billing/wallet/topup";
    request: WalletTopupRequest;
    response: LedgerAccountResponse;
  };
  holdOrderEscrow: {
    method: "POST";
    path: "/api/v1/billing/escrow/hold";
    request: EscrowHoldRequest;
    response: EscrowHoldListResponse;
  };
  releaseSubOrderEscrow: {
    method: "POST";
    path: "/api/v1/billing/escrow/release";
    request: EscrowReleaseRequest;
    response: EscrowHoldResponse;
  };
  evaluateDataForCreditLimit: {
    method: "POST";
    path: "/api/v1/billing/credit-scoring/evaluate";
    request: void;
    response: LedgerAccountResponse;
  };
  createPosStore: {
    method: "POST";
    path: "/api/v1/pos-sync/stores";
    request: CreatePosStoreRequest;
    response: PosStoreResponse;
  };
  syncPosDeltaBatch: {
    method: "POST";
    path: "/api/v1/pos-sync/delta";
    request: PosDeltaSyncBatchRequest;
    response: PosDeltaSyncBatchResponse;
  };
  oneClickWaybillInbound: {
    method: "POST";
    path: "/api/v1/pos-sync/one-click-inbound";
    request: OneClickWaybillInboundRequest;
    response: OneClickWaybillInboundResponse;
  };
  generateDidoxEhfDocument: {
    method: "POST";
    path: "/api/v1/integrations/didox/ehf";
    request: GenerateDidoxEhfRequest;
    response: EhfDocumentResponse;
  };
  registerSoliqOfdFiscalReceipt: {
    method: "POST";
    path: "/api/v1/integrations/soliq/ofd-receipt";
    request: RegisterOfdReceiptRequest;
    response: OfdFiscalReceiptResponse;
  };
  dbazarConnectExternalInbound: {
    method: "POST";
    path: "/api/v1/integrations/dbazar-connect/inbound";
    request: DbazarConnectInboundRequest;
    response: DbazarConnectInboundResponse;
  };
  createOrAssignShipment: {
    method: "POST";
    path: "/api/v1/logistics/shipments";
    request: AssignShipmentRequest;
    response: ShipmentResponse;
  };
  updateShipmentGpsAndStatus: {
    method: "POST";
    path: "/api/v1/logistics/shipments/{shipment_id}/gps";
    request: UpdateShipmentGpsRequest;
    response: ShipmentResponse;
  };
  confirmShipmentProofOfDelivery: {
    method: "POST";
    path: "/api/v1/logistics/shipments/{shipment_id}/pod";
    request: ConfirmPodRequest;
    response: ShipmentResponse;
  };
}
