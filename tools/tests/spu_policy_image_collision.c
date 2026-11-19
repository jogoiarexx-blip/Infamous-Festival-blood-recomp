/* Synthetic guest instructions; no game assets or extracted code. */
#include "spu_helpers.h"
#include "spu_interp.h"
#include "spu_overlay_residency.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
uint8_t *vm_base;
uint32_t ppu_vm_size;
extern void spu_begin_image(int);
extern void spu_register_function(uint32_t, void (*)(spu_context *));
extern int spu_run_with_halt(void (*)(spu_context *), spu_context *);
extern void spu_halt(spu_context *);
extern int
spu_overlay_register_verified_region(uint32_t, uint32_t, uint32_t, int,
                                     const spu_overlay_code_segment *,
                                     unsigned);
extern void spu_overlay_note_get(spu_context *, uint32_t, const uint8_t *,
                                 uint32_t);
static spu_context ctx;
static int wrong_calls, finished, own_calls;
static void finish(spu_context *c) {
  finished++;
  c->status = SPU_STATUS_STOPPED_BY_STOP;
  spu_halt(c);
}
static void unrelated(spu_context *c) {
  wrong_calls++;
  spu_ls_write32(c, 0, 0x30303030);
  finish(c);
}
static void correct(spu_context *c) {
  own_calls++;
  c->gpr[2] = c->gpr[1];
  finish(c);
}
static void enter(spu_context *c) {
  c->pc = 0x6000;
  g_spu_trampoline_fn = spu_indirect_branch;
}
int main(int argc, char **argv) {
  spu_context_init(&ctx, 0);
  ctx.image_id = 2;
  ctx.policy_mode = 1;
  ctx.status = SPU_STATUS_RUNNING;
  ctx.gpr[1] = spu_splat_u32(0x1234);
  spu_begin_image(1);
  spu_register_function(0x6000, unrelated);
  spu_begin_image(2);
  spu_register_function(0x240, finish);
  spu_begin_image(0);
  spu_ls_write32(&ctx, 0, 0x30000000); /* preserved interrupt-vector sentinel */
  spu_ls_write32(&ctx, 0x6000, 0x04000082); /* ori $2,$1,0: full interpreter */
  spu_ls_write32(&ctx, 0x6004, 0x30004800); /* bra 0x240: primary image */
  if (argc > 1 && (!strcmp(argv[1], "bounded") || !strcmp(argv[1], "owned") ||
                   !strcmp(argv[1], "rejected"))) {
    static const uint8_t bytes[] = {4, 0, 0, 0x82, 0x30, 0, 0x48, 0};
    const spu_overlay_code_segment seg = {0x6000, sizeof bytes, bytes};
    if (!strcmp(argv[1], "owned") || !strcmp(argv[1], "rejected")) {
      spu_begin_image(222);
      spu_register_function(0x6000, correct);
      spu_begin_image(0);
    }
    if (!spu_overlay_register_verified_region(0x900000, 0x6000, 8, 222, &seg,
                                              1))
      return 2;
    if (!strcmp(argv[1], "rejected"))
      ctx.ls[0x6001] = 0x40; /* ori immediate 0x100, valid differing code */
    spu_overlay_note_get(&ctx, 0x900000, ctx.ls + 0x6000, 8);
  }
  spu_run_with_halt(enter, &ctx);
  int owned = argc > 1 && !strcmp(argv[1], "owned");
  uint32_t expected =
      argc > 1 && !strcmp(argv[1], "rejected") ? 0x1334 : 0x1234;
  int ok = finished == 1 && wrong_calls == 0 && own_calls == owned &&
           ctx.gpr[2]._u32[0] == expected &&
           spu_ls_read32(&ctx, 0) == 0x30000000;
  printf("policy-image-collision %s: %s wrong_calls=%d finished=%d vector=%08X "
         "r2=%08X\n",
         argc > 1 ? argv[1] : "unbounded", ok ? "PASS" : "FAIL", wrong_calls,
         finished, spu_ls_read32(&ctx, 0), ctx.gpr[2]._u32[0]);
  return ok ? 0 : 1;
}
/* Link-only boundaries outside this CPU-only fixture. Fail if any is reached.
 */
/* spu_workload.c can retain the LV2 runner's publication calls at link time;
 * this fixture runs its own context directly, without an LV2 SPU thread. */
void spu_thread_publish_ctx(uint32_t tid, void *c) {
  (void)tid;
  (void)c;
  abort();
}
void ppu_resv_break_store(uint64_t ea) {
  (void)ea;
  abort();
}
void ps3_ww_report_inline(uint32_t a, uint64_t v, int w) {
  (void)a;
  (void)v;
  (void)w;
  abort();
}
unsigned long long ps3_ms_now(void) { abort(); }
uint32_t g_ww_lo = 0xFFFFFFFFu, g_ww_hi;
int g_resv_store_active;
uint32_t g_barrier_sync_watch;
uint32_t g_ydkj_real_spurs_ea, g_ydkj_real_taskset_ea, g_ydkj_real_taskid;
void spurs_ef_set_from_spu(uint32_t ea, uint16_t bits) {
  (void)ea;
  (void)bits;
  abort();
}
void ydkj_wake_all_event_flags(void) { abort(); }
void spurs_pm_build_context(spu_context *c, uint32_t a, uint32_t b,
                            uint32_t d) {
  (void)c;
  (void)a;
  (void)b;
  (void)d;
  abort();
}
uint32_t g_spu_image_src_ea, g_spu_image_ls_start, g_spu_image_span;

/* Windows channel boundaries are not used by this CPU-only fixture. */
uint32_t spu_thread_bound_queue(uint32_t a, uint32_t b) {
  (void)a;
  (void)b;
  abort();
}
int sys_event_queue_receive_host(uint32_t a, uint64_t b[3], volatile int *c) {
  (void)a;
  (void)b;
  (void)c;
  abort();
}
uint32_t g_ps3_ro_lo, g_ps3_ro_hi;
