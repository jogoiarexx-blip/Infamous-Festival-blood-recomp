/* Compare locally captured kernel inputs; no game data is embedded here.
 * Format per numbered input: 128 native little-endian 16-byte registers,
 * followed by the complete 256 KiB LS. Capture immediately before LS 0x6C30.
 * The finish callback is an isolated test boundary at the original return PC;
 * it is never installed into the running game or used to complete a game job.
 */
#include "spu_helpers.h"
#include "spu_interp.h"
#include "spu_overlay_residency.h"
extern void spu_overlay_note_get(spu_context *, uint32_t, const uint8_t *,
                                 uint32_t);
extern uint64_t g_spu_interp_steps;
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
uint8_t *vm_base;
uint32_t ppu_vm_size;
extern void spu_begin_image(int);
extern void spu_register_function(uint32_t, void (*)(spu_context *));
extern int spu_run_with_halt(void (*)(spu_context *), spu_context *);
extern void spu_halt(spu_context *);
extern void fobdata0_spu_recomp_register(void);
extern void fobdata0_spu_func_00006C30(spu_context *);
extern void fobdata1_spu_recomp_register(void);
extern void fobdata1_spu_func_00006C30(spu_context *);
extern void fobdata2_spu_recomp_register(void);
extern void fobdata2_spu_func_00006C30(spu_context *);
extern void fobdata3_spu_recomp_register(void);
extern void fobdata3_spu_func_00006C30(spu_context *);
extern void fobdata4_spu_recomp_register(void);
extern void fobdata4_spu_func_00006C30(spu_context *);
static spu_context ref, native;
static void finish(spu_context *c) {
  c->status = SPU_STATUS_STOPPED_BY_STOP;
  spu_halt(c);
}
static unsigned long long state_hash(const spu_context *c) {
  const unsigned char *g = (const unsigned char *)c->gpr;
  unsigned long long h = 1469598103934665603ULL;
  for (unsigned i = 0; i < sizeof(c->gpr); i++)
    h = (h ^ g[i]) * 1099511628211ULL;
  for (unsigned i = 0; i < SPU_LS_SIZE; i++)
    h = (h ^ c->ls[i]) * 1099511628211ULL;
  return h;
}
int main(int argc, char **argv) {
  if (argc != 2)
    return 2;
  vm_base = calloc(1, 0x1000000);
  ppu_vm_size = 0x1000000;
  void (*entries[5])(spu_context *) = {
      fobdata0_spu_func_00006C30, fobdata1_spu_func_00006C30,
      fobdata2_spu_func_00006C30, fobdata3_spu_func_00006C30,
      fobdata4_spu_func_00006C30};
  const uint32_t eas[5] = {0x8C5500, 0x8C5880, 0x8C6480, 0x8C6C80, 0x8C7880};
  const uint32_t sizes[5] = {784, 2960, 1936, 2960, 5392};
  int failed = 0;
  for (unsigned i = 0; i < 5; i++) {
    spu_context_init(&ref, 0);
    spu_context_init(&native, 0);
    char path[512];
    snprintf(path, sizeof(path), "%s/%u.bin", argv[1], i);
    FILE *f = fopen(path, "rb");
    if (!f)
      return 3;
    if (fread(ref.gpr, 1, sizeof(ref.gpr), f) != sizeof(ref.gpr) ||
        fread(ref.ls, 1, SPU_LS_SIZE, f) != SPU_LS_SIZE)
      return 4;
    fclose(f);
    memcpy(native.gpr, ref.gpr, sizeof(ref.gpr));
    memcpy(native.ls, ref.ls, SPU_LS_SIZE);
    unsigned stop = ref.gpr[0]._u32[0] & SPU_LS_MASK;
    /* No image 999 is registered; the reference cannot rejoin native code. */
    ref.image_id = 999;
    ref.pc = 0x6C30;
    ref.status = SPU_STATUS_RUNNING;
    if (spu_lifted_lookup(&ref, 0x6C30))
      return 6;
    g_spu_interp_steps = 0;
    clock_t t0 = clock();
    spu_interp_run_until(&ref, 0x6C30, stop);
    double it = (double)(clock() - t0) / CLOCKS_PER_SEC;
    if (ref.pc != stop || g_spu_interp_steps == 0) {
      fprintf(stderr, "kernel%u interpreter pc=%X expected=%X\n", i, ref.pc,
              stop);
      return 5;
    }
    spu_begin_image(2);
    spu_register_function(stop, finish);
    spu_begin_image(0);
    native.image_id = 2;
    /* A mismatched DMA must refuse the compiled owner, then an exact reload
     * must select THIS module, despite all five sharing the same LS entry. */
    native.ls[0x6C30] ^= 1;
    spu_overlay_note_get(&native, eas[i], native.ls + 0x6C00, sizes[i]);
    if (spu_lifted_lookup(&native, 0x6C30)) {
      fprintf(stderr, "kernel%u accepted differing code\n", i);
      return 7;
    }
    native.ls[0x6C30] ^= 1;
    spu_overlay_note_get(&native, eas[i], native.ls + 0x6C00, sizes[i]);
    if (spu_lifted_lookup(&native, 0x6C30) != entries[i]) {
      fprintf(stderr, "kernel%u wrong compiled owner\n", i);
      return 8;
    }
    native.pc = 0x6C30;
    native.status = SPU_STATUS_RUNNING;
    t0 = clock();
    spu_run_with_halt(entries[i], &native);
    double nt = (double)(clock() - t0) / CLOCKS_PER_SEC;
    unsigned gr = 0, ls = 0;
    for (unsigned x = 0; x < 128; x++)
      if (memcmp(&ref.gpr[x], &native.gpr[x], 16)) {
        if (gr++ < 4)
          fprintf(stderr, "kernel%u GPR%u ref=%08X native=%08X\n", i, x,
                  ref.gpr[x]._u32[0], native.gpr[x]._u32[0]);
      }
    for (unsigned x = 0; x < SPU_LS_SIZE; x++)
      if (ref.ls[x] != native.ls[x]) {
        if (ls++ < 4)
          fprintf(stderr, "kernel%u LS%05X ref=%02X native=%02X\n", i, x,
                  ref.ls[x], native.ls[x]);
      }
    printf("kernel=%u gpr_diff=%u ls_diff=%u ref_pc=%X native_pc=%X "
           "state_hash=%016llX interpreted=%.3fs native=%.3fs\n",
           i, gr, ls, ref.pc, native.pc, state_hash(&native), it, nt);
    fflush(stdout);
    failed += gr || ls || native.pc != stop;
  }
  return failed ? 1 : 0;
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
