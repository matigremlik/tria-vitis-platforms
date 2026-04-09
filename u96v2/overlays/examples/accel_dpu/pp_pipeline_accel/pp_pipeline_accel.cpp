#include <ap_int.h>
#include <stdint.h>

extern "C" void pp_pipeline_accel(
    const uint8_t* in_bgr,
    int8_t* out_rgb_q,
    int in_w,
    int in_h,
    int fix_scale
) {
#pragma HLS INTERFACE m_axi     port=in_bgr    offset=slave bundle=gmem0 depth=1
#pragma HLS INTERFACE m_axi     port=out_rgb_q offset=slave bundle=gmem1 depth=1

#pragma HLS INTERFACE s_axilite port=in_bgr    bundle=control
#pragma HLS INTERFACE s_axilite port=out_rgb_q bundle=control
#pragma HLS INTERFACE s_axilite port=in_w      bundle=control
#pragma HLS INTERFACE s_axilite port=in_h      bundle=control
#pragma HLS INTERFACE s_axilite port=fix_scale bundle=control
#pragma HLS INTERFACE s_axilite port=return    bundle=control

    const int OUT_W = 224;
    const int OUT_H = 224;

    // Force no unrolling
#pragma HLS INLINE off

    for (int y = 0; y < OUT_H; y++) {
    #pragma HLS LOOP_TRIPCOUNT min=224 max=224
        int src_y = (int)((long long)y * in_h / OUT_H);

        for (int x = 0; x < OUT_W; x++) {
        #pragma HLS LOOP_TRIPCOUNT min=224 max=224
        #pragma HLS PIPELINE II=8   
        #pragma HLS UNROLL factor=1

            int src_x = (int)((long long)x * in_w / OUT_W);

            int in_idx  = (src_y * in_w + src_x) * 3;
            uint8_t b = in_bgr[in_idx + 0];
            uint8_t g = in_bgr[in_idx + 1];
            uint8_t r = in_bgr[in_idx + 2];

            uint8_t rq = (uint16_t(r) * (uint16_t)fix_scale) / 255;
            uint8_t gq = (uint16_t(g) * (uint16_t)fix_scale) / 255;
            uint8_t bq = (uint16_t(b) * (uint16_t)fix_scale) / 255;

            int out_idx = (y * OUT_W + x) * 3;
            out_rgb_q[out_idx + 0] = (int8_t)rq;
            out_rgb_q[out_idx + 1] = (int8_t)gq;
            out_rgb_q[out_idx + 2] = (int8_t)bq;
        }
    }
}
