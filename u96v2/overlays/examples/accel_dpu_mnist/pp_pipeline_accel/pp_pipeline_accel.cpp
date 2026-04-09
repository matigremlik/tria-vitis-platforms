#include <ap_int.h>
#include <stdint.h>

extern "C" void pp_pipeline_accel(
    const ap_uint<64>* in_gray,
    uint32_t* out_gray_q,
    int in_w,
    int in_h,
    int fix_scale
) {
#pragma HLS INTERFACE m_axi     port=in_gray    offset=slave bundle=gmem0 depth=98 max_widen_bitwidth=64
#pragma HLS INTERFACE m_axi     port=out_gray_q offset=slave bundle=gmem1 depth=784 max_widen_bitwidth=32

#pragma HLS INTERFACE s_axilite port=in_gray    bundle=control
#pragma HLS INTERFACE s_axilite port=out_gray_q bundle=control
#pragma HLS INTERFACE s_axilite port=in_w       bundle=control
#pragma HLS INTERFACE s_axilite port=in_h       bundle=control
#pragma HLS INTERFACE s_axilite port=fix_scale  bundle=control
#pragma HLS INTERFACE s_axilite port=return     bundle=control

    const int W = 28;
    const int H = 28;
    const int PIXELS = W * H;
    const int INPUT_WORD_BYTES = 8;
    const int INPUT_WORDS = (PIXELS + INPUT_WORD_BYTES - 1) / INPUT_WORD_BYTES;

    uint8_t scale_lut[256];
#pragma HLS ARRAY_PARTITION variable=scale_lut complete

#pragma HLS INLINE off

    for (int i = 0; i < 256; ++i) {
#pragma HLS PIPELINE II=1
        int scaled = (i * fix_scale + 127) / 255;
        if (scaled > 127) {
            scaled = 127;
        }
        scale_lut[i] = (uint8_t)scaled;
    }

    ap_uint<64> word = 0;
    int next_word_idx = 0;
    int byte_offset = 0;

    if (INPUT_WORDS > 0) {
        word = in_gray[0];
        next_word_idx = 1;
    }

    for (int pix = 0; pix < PIXELS; ++pix) {
#pragma HLS LOOP_TRIPCOUNT min=784 max=784
#pragma HLS PIPELINE II=1
        ap_uint<64> shifted = word >> (byte_offset * 8);
        uint8_t gray = (uint8_t)shifted.range(7, 0);
        uint8_t gray_q = scale_lut[gray];

        out_gray_q[pix] = ((uint32_t)gray_q << 16) |
                          ((uint32_t)gray_q << 8)  |
                          (uint32_t)gray_q;

        ++byte_offset;
        if (byte_offset == INPUT_WORD_BYTES) {
            byte_offset = 0;
            if (next_word_idx < INPUT_WORDS) {
                word = in_gray[next_word_idx];
                ++next_word_idx;
            } else {
                word = 0;
            }
        }
    }
}
