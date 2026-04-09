#include <ap_int.h>
#include <stdint.h>

extern "C" void pp_pipeline_accel(
    const ap_uint<64>* in_bgr,
    uint32_t* out_rgb_q,
    int in_w,
    int in_h,
    int fix_scale
) {
#pragma HLS INTERFACE m_axi     port=in_bgr    offset=slave bundle=gmem0 depth=18816 max_widen_bitwidth=64
#pragma HLS INTERFACE m_axi     port=out_rgb_q offset=slave bundle=gmem1 depth=50176 max_widen_bitwidth=32

#pragma HLS INTERFACE s_axilite port=in_bgr    bundle=control
#pragma HLS INTERFACE s_axilite port=out_rgb_q bundle=control
#pragma HLS INTERFACE s_axilite port=in_w      bundle=control
#pragma HLS INTERFACE s_axilite port=in_h      bundle=control
#pragma HLS INTERFACE s_axilite port=fix_scale bundle=control
#pragma HLS INTERFACE s_axilite port=return    bundle=control

    const int W = 224;
    const int H = 224;
    const int PIXELS = W * H;
    const int INPUT_WORD_BYTES = 8;
    const int INPUT_BYTES = PIXELS * 3;
    const int INPUT_WORDS = (INPUT_BYTES + INPUT_WORD_BYTES - 1) / INPUT_WORD_BYTES;

    uint8_t scale_lut[256];
#pragma HLS ARRAY_PARTITION variable=scale_lut complete

#pragma HLS INLINE off

    for (int i = 0; i < 256; i++) {
#pragma HLS PIPELINE II=1
        scale_lut[i] = (i * fix_scale) / 255;
    }

    if (in_w != W || in_h != H) {
        return;
    }

    ap_uint<64> word_lo = 0;
    ap_uint<64> word_hi = 0;
    int next_word_idx = 0;
    int byte_offset = 0;

    if (INPUT_WORDS > 0) {
        word_lo = in_bgr[0];
        next_word_idx = 1;
    }
    if (INPUT_WORDS > 1) {
        word_hi = in_bgr[1];
        next_word_idx = 2;
    }

    for (int pix = 0; pix < PIXELS; pix++) {
#pragma HLS LOOP_TRIPCOUNT min=50176 max=50176
#pragma HLS PIPELINE II=1
        uint8_t b = 0;
        uint8_t g = 0;
        uint8_t r = 0;

        switch (byte_offset) {
        case 0:
            b = (uint8_t)word_lo.range(7, 0);
            g = (uint8_t)word_lo.range(15, 8);
            r = (uint8_t)word_lo.range(23, 16);
            break;
        case 1:
            b = (uint8_t)word_lo.range(15, 8);
            g = (uint8_t)word_lo.range(23, 16);
            r = (uint8_t)word_lo.range(31, 24);
            break;
        case 2:
            b = (uint8_t)word_lo.range(23, 16);
            g = (uint8_t)word_lo.range(31, 24);
            r = (uint8_t)word_lo.range(39, 32);
            break;
        case 3:
            b = (uint8_t)word_lo.range(31, 24);
            g = (uint8_t)word_lo.range(39, 32);
            r = (uint8_t)word_lo.range(47, 40);
            break;
        case 4:
            b = (uint8_t)word_lo.range(39, 32);
            g = (uint8_t)word_lo.range(47, 40);
            r = (uint8_t)word_lo.range(55, 48);
            break;
        case 5:
            b = (uint8_t)word_lo.range(47, 40);
            g = (uint8_t)word_lo.range(55, 48);
            r = (uint8_t)word_lo.range(63, 56);
            break;
        case 6:
            b = (uint8_t)word_lo.range(55, 48);
            g = (uint8_t)word_lo.range(63, 56);
            r = (uint8_t)word_hi.range(7, 0);
            break;
        default:
            b = (uint8_t)word_lo.range(63, 56);
            g = (uint8_t)word_hi.range(7, 0);
            r = (uint8_t)word_hi.range(15, 8);
            break;
        }

        uint8_t bq = scale_lut[b];
        uint8_t gq = scale_lut[g];
        uint8_t rq = scale_lut[r];

        out_rgb_q[pix] = ((uint32_t)rq << 16) |
                         ((uint32_t)gq << 8)  |
                         (uint32_t)bq;

        byte_offset += 3;
        if (byte_offset >= INPUT_WORD_BYTES) {
            byte_offset -= INPUT_WORD_BYTES;
            word_lo = word_hi;
            if (next_word_idx < INPUT_WORDS) {
                word_hi = in_bgr[next_word_idx];
                next_word_idx++;
            } else {
                word_hi = 0;
            }
        }
    }
}
