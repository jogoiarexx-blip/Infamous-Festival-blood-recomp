
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
typedef void *LPVOID;
typedef unsigned long DWORD;
#define WINAPI
#define Sleep(ms) ((void)(ms))
#define ps3_thread_name(...) ((void)0)
static struct { uint32_t entry_ea, jc_ea, size_desc; long running; } s_jobchains[1];
typedef uint32_t u32;
typedef uint64_t u64;
#define SPURS_JOB_TLS
#define SPURS_EVENT_PORT 0x5350555253ULL
#define PS3_LOG_FIRST(n, l) ((n)++ < (l))
static unsigned char mem[4096];
static u32 s_spurs_event_queue[] = {1, 2, 6};
static int s_spurs_event_queue_n = 3;
u32 g_spurs_job_mbox, g_spurs_job_mbox_intr, g_spurs_job_cmd,
    g_spurs_job_ls_handle;
int g_spurs_job_mbox_valid;
static int d3_probe_valid;
static unsigned events, premature, foreign, published, jobs_run;
static u64 spurs_event_data3_probe(void) { return 0; }
static u64 vm_read64(u32 a) {
  u64 v = 0;
  for (unsigned i = 0; i < 8; i++)
    v = v * 256 + mem[a + i];
  return v;
}
static void word(u32 a, u64 v) {
  for (unsigned i = 0; i < 8; i++)
    mem[a + 7 - i] = (unsigned char)(v >> (i * 8));
}
static int sys_event_queue_push_by_id(u32 q, u64 source, u64 d1, u64 d2,
                                      u64 d3) {
  (void)source;
  (void)d1;
  (void)d2;
  (void)d3;
  events++;
  premature += !published;
  foreign += q != 6;
  return 0;
}
static int jg_wait(u32 ea) {
  (void)ea;
  return 1;
}
static void jc_run_one_job(u32 ea, int index, u32 size) {
  (void)index;
  (void)size;
  jobs_run++;
  if (ea == 0x280) {
    published = 1;
    sys_event_queue_push_by_id(6, 0xFFFFFFFF53505501ULL, 0, 0, 0);
  }
}

/* Runtime walker functions are inserted here by the runner. */
@RUNTIME_WALKER@

static void run_chain(void) {
  s_jobchains[0].entry_ea=0x100;
  s_jobchains[0].jc_ea=0x400;
  s_jobchains[0].size_desc=128;
  s_jobchains[0].running=1;
  jc_thread((LPVOID)(intptr_t)0);
}

int main(void) {
  int failed = 0;
  word(0x100, 0x200);
  word(0x108, 0x280);
  word(0x110, 127);
  run_chain();
  if (events != 1 || premature || foreign || jobs_run != 2 || s_jobchains[0].running) {
    fprintf(
        stderr,
        "FAIL ordered publisher: events=%u premature=%u foreign=%u jobs=%u\n",
        events, premature, foreign, jobs_run);
    failed++;
  }
  events = premature = foreign = published = jobs_run = 0;
  word(0x100, 0x200);
  word(0x108, 127);
  run_chain();
  if (events || jobs_run != 1 || s_jobchains[0].running) {
    fprintf(stderr, "FAIL silent job + END: events=%u jobs=%u\n", events,
            jobs_run);
    failed++;
  }
  events = premature = foreign = published = jobs_run = 0;
  word(0x100, 7);
  run_chain();
  if (events || jobs_run || s_jobchains[0].running) {
    fprintf(stderr, "FAIL ABORT emitted event\n");
    failed++;
  }
  if (!failed)
    puts("PASS 3 jobchain event ordering cases");
  return failed ? 1 : 0;
}
