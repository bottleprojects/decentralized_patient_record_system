#include "device_authentication.h"

DeviceAuthenticator::DeviceAuthenticator(const char* deviceId, const char* secretKey)
    : _deviceId(deviceId), _secretKey(secretKey) {}

String DeviceAuthenticator::computeHMAC(
    const char* sessionId,
    uint32_t sequenceNumber,
    const char* timestamp,
    int heartRate,
    int spo2,
    uint32_t irValue,
    bool leadsOff
) {
    // Construct canonical string matching backend validator format
    String canonical = String(_deviceId) + "|" +
                       String(sessionId ? sessionId : "") + "|" +
                       String(sequenceNumber) + "|" +
                       String(timestamp ? timestamp : "") + "|" +
                       String(heartRate) + "|" +
                       String(spo2) + "|" +
                       String(irValue) + "|" +
                       (leadsOff ? "True" : "False");

    byte hmacResult[32];
    mbedtls_md_context_t ctx;
    mbedtls_md_type_t md_type = MBEDTLS_MD_SHA256;

    mbedtls_md_init(&ctx);
    mbedtls_md_setup(&ctx, mbedtls_md_info_from_type(md_type), 1);
    mbedtls_md_hmac_starts(&ctx, (const unsigned char*)_secretKey, strlen(_secretKey));
    mbedtls_md_hmac_update(&ctx, (const unsigned char*)canonical.c_str(), canonical.length());
    mbedtls_md_hmac_finish(&ctx, hmacResult);
    mbedtls_md_free(&ctx);

    // Convert to hex string
    char hexBuffer[65];
    for (int i = 0; i < 32; i++) {
        sprintf(hexBuffer + (i * 2), "%02x", hmacResult[i]);
    }
    hexBuffer[64] = 0;

    return String(hexBuffer);
}

