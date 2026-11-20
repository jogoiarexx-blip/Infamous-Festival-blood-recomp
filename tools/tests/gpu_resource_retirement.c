/* CPU-only objects exercise the actual SDK control flow; no GPU or game data.
 */

#include <setjmp.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
typedef uint32_t u32;
typedef uint64_t u64;
typedef int32_t HRESULT;
typedef unsigned long DWORD;
typedef void *HANDLE;
#define FRAME_COUNT 2
#define WAIT_TIMEOUT 258
#define WAIT_OBJECT_0 0
#define WAIT_FAILED 0xFFFFFFFFUL
#define S_OK 0
#define FAILED(x) ((HRESULT)(x) < 0)
#define SUCCEEDED(x) ((HRESULT)(x) >= 0)
static unsigned released, fatals, failures;
static jmp_buf fatal_env;
static u64 completed;
static DWORD wait_result = WAIT_TIMEOUT;
static int instant;
static HRESULT signal_result, set_event_result, device_reason;
typedef struct ID3D12Resource ID3D12Resource;
typedef struct FakeFence FakeFence;
typedef struct FakeQueue FakeQueue;
typedef struct FakeSwap FakeSwap;
typedef struct FakeDevice FakeDevice;
typedef struct {
  unsigned long (*Release)(ID3D12Resource *);
} RV;
struct ID3D12Resource {
  const RV *lpVtbl;
};
static unsigned long release_resource(ID3D12Resource *r) {
  (void)r;
  released++;
  return 0;
}
static RV rv = {release_resource};
static ID3D12Resource resource = {&rv};
typedef struct {
  u64 (*GetCompletedValue)(FakeFence *);
  HRESULT (*SetEventOnCompletion)(FakeFence *, u64, HANDLE);
} FV;
struct FakeFence {
  const FV *lpVtbl;
};
static u64 get_completed(FakeFence *f) {
  (void)f;
  return completed;
}
static HRESULT set_event(FakeFence *f, u64 v, HANDLE h) {
  (void)f;
  (void)v;
  (void)h;
  return set_event_result;
}
static FV fv = {get_completed, set_event};
static FakeFence fence = {&fv};
typedef struct {
  HRESULT (*Signal)(FakeQueue *, FakeFence *, u64);
} QV;
struct FakeQueue {
  const QV *lpVtbl;
};
static HRESULT signal_gpu(FakeQueue *q, FakeFence *f, u64 v) {
  (void)q;
  (void)f;
  if (instant && v > completed)
    completed = v;
  return signal_result;
}
static QV qv = {signal_gpu};
static FakeQueue queue = {&qv};
typedef struct {
  u32 (*GetCurrentBackBufferIndex)(FakeSwap *);
} SV;
struct FakeSwap {
  const SV *lpVtbl;
};
static u32 get_index(FakeSwap *s) {
  (void)s;
  return 1;
}
static SV sv = {get_index};
static FakeSwap swap = {&sv};
typedef struct {
  HRESULT (*GetDeviceRemovedReason)(FakeDevice *);
} DV;
struct FakeDevice {
  const DV *lpVtbl;
};
static HRESULT get_reason(FakeDevice *d) {
  (void)d;
  return device_reason;
}
static DV dv = {get_reason};
static FakeDevice device = {&dv};
static struct {
  u32 frame_index;
  u64 fence_values[2];
  FakeQueue *cmd_queue;
  FakeFence *fence;
  FakeSwap *swap_chain;
  FakeDevice *device;
  HANDLE fence_event;
  int initialized;
  u32 width, height;
  struct {
    ID3D12Resource *res;
    u32 w, h;
  } off_rt[4];
} s_d3d;
static unsigned s_dbg_frame, submitted_pso_count;
static ID3D12Resource *submitted_psos[32];
static DWORD WaitForSingleObject(HANDLE h, DWORD ms) {
  (void)h;
  (void)ms;
  return wait_result;
}
static void fake_abort(void) {
  fatals++;
  longjmp(fatal_env, 1);
}
#define abort() fake_abort()
static void dred_report(void) {}

/* INSERT_RUNTIME_IMPLEMENTATION */

static void init(void) {
  completed = 1000;
  for (unsigned i = 0; i < 2; i++)
    grave_flush(i);
  released = fatals = 0;
  memset(&s_d3d, 0, sizeof s_d3d);
  s_d3d.fence = &fence;
  s_d3d.cmd_queue = &queue;
  s_d3d.swap_chain = &swap;
  s_d3d.device = &device;
  s_d3d.initialized = 1;
  signal_result = set_event_result = device_reason = 0;
  instant = 1;
  wait_result = WAIT_TIMEOUT;
}
static void pending_next_frame(void) {
  s_d3d.frame_index = 1;
  defer_release(&resource);
  s_d3d.frame_index = 0;
  s_d3d.fence_values[0] = 9;
  s_d3d.fence_values[1] = 5;
}
static void expect_retained(const char *name) {
  if (released || !fatals) {
    fprintf(stderr, "FAIL %s: released=%u fatal=%u\n", name, released, fatals);
    failures++;
  }
}
int main(void) {
  init();
  for (int i = 0; i < 513; i++)
    defer_release(&resource);
  if (released) {
    fprintf(stderr, "FAIL retirement overflow released pending resource\n");
    failures++;
  }
  grave_flush(0);
  if (released != 513) {
    fprintf(stderr, "FAIL retirement overflow lost references\n");
    failures++;
  }
  init();
  pending_next_frame();
  completed = 0;
  instant = 0;
  if (!setjmp(fatal_env))
    move_to_next_frame();
  expect_retained("timeout");
  init();
  pending_next_frame();
  completed = UINT64_MAX;
  instant = 0;
  if (!setjmp(fatal_env))
    move_to_next_frame();
  expect_retained("removed device");
  init();
  s_d3d.frame_index = 0;
  defer_release(&resource);
  s_d3d.frame_index = 1;
  defer_release(&resource);
  if (!setjmp(fatal_env))
    shutdown_retire_only();
  if (released != 2 || fatals || s_grave[0].items || s_grave[1].items ||
      s_grave[0].capacity || s_grave[1].capacity) {
    fprintf(stderr, "FAIL shutdown did not drain/free both retirement slots\n");
    failures++;
  }
  init();
  pending_next_frame();
  signal_result = (HRESULT)0x80004005u;
  if (!setjmp(fatal_env))
    move_to_next_frame();
  expect_retained("queue Signal failure");
  init();
  pending_next_frame();
  completed = 0;
  instant = 0;
  set_event_result = (HRESULT)0x80004005u;
  if (!setjmp(fatal_env))
    move_to_next_frame();
  expect_retained("SetEventOnCompletion failure");
  init();
  pending_next_frame();
  completed = 0;
  instant = 0;
  wait_result = WAIT_OBJECT_0;
  if (!setjmp(fatal_env))
    move_to_next_frame();
  expect_retained("stale signaled event");
  init();
  pending_next_frame();
  if (!setjmp(fatal_env))
    move_to_next_frame();
  if (released != 1 || fatals) {
    fprintf(stderr, "FAIL completed fence did not release resources\n");
    failures++;
  }
  printf("GPU retirement: %s 8 cases (%u failures)\n",
         failures ? "FAIL" : "PASS", failures);
  return failures ? 1 : 0;
}
