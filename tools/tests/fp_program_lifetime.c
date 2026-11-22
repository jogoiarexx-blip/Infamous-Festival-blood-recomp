#include "rsx_fp_decompiler.h"
#include <stdio.h>
#include <string.h>
#define VP_FP_UCODE_BYTES 4096u
typedef struct { u32 fp_addr, fp_ucode_size, fp_ucode_ea; u8 fp_ucode[VP_FP_UCODE_BYTES]; } D3D12DrawRecord;
static u8 ram[8192];
u8* vm_base = ram;
u32 cellGcmResolveLocated(int local, u32 offset) { (void)local; return offset == 0x100u ? offset : 0xFFFFFFFFu; }
/* ACTUAL_SNAPSHOT_HELPER */
static unsigned failures, checks;
#define CHECK(c, n) do { checks++; if(!(c)){failures++;fprintf(stderr,"FAIL: %s\n",n);} }while(0)
static void word(u8* p,u32 w) { u32 b=(w<<16)|(w>>16);p[0]=b>>24;p[1]=b>>16;p[2]=b>>8;p[3]=b; }
static void program(float value) {
    u8* p=ram+0x100;memset(p,0,4096);
    word(p, (1u<<24)|(15u<<9)|1u); /* MOV r0, inline constant; END */
    word(p+4,2u|0x1C9C800u); /* identity swizzle + unconditional */
    word(p+8,0);word(p+12,0);
    u32 bits;memcpy(&bits,&value,4);for(int i=0;i<4;i++)word(p+16+i*4,bits);
}
static const u8* bytes(D3D12DrawRecord* d) {
#ifdef LEGACY_CONTROL
    return ram+d->fp_ucode_ea;
#else
    return d->fp_ucode;
#endif
}
int main(void) {
    D3D12DrawRecord a={.fp_addr=0x102},b={.fp_addr=0x102};
    char expected[16384],actual[16384];float constants[8];
    program(0.25f);rsx_fp_decompile(ram+0x100,32,0x40,expected,sizeof expected);fp_record_program(&a);
    program(0.75f);fp_record_program(&b);memset(ram+0x100,0,4096);
    rsx_fp_decompile(bytes(&a),a.fp_ucode_size,0x40,actual,sizeof actual);
    CHECK(!strcmp(expected,actual),"guest reuse must not change first draw's generated shader");
    CHECK(rsx_fp_extract_consts(bytes(&a),a.fp_ucode_size,constants,2)==1 && constants[0]==0.25f,"first draw keeps its inline constant");
    CHECK(rsx_fp_extract_consts(bytes(&b),b.fp_ucode_size,constants,2)==1 && constants[0]==0.75f,"same address records a distinct later version");
    CHECK(a.fp_ucode_size==32,"END includes its inline payload but excludes following memory");
    D3D12DrawRecord moved=a;memset(a.fp_ucode,0,sizeof a.fp_ucode);
    CHECK(rsx_fp_extract_consts(bytes(&moved),moved.fp_ucode_size,constants,2)==1 && constants[0]==0.25f,"draw record relocation keeps the snapshot");
    a.fp_addr=0;fp_record_program(&a);CHECK(a.fp_ucode_size==0,"unbound program clears stale snapshot");
    a.fp_addr=0x202;fp_record_program(&a);CHECK(a.fp_ucode_size==0,"unmapped address clears stale snapshot");
    a.fp_addr=0x102;memset(ram+0x100,0,4096);fp_record_program(&a);
    CHECK(a.fp_ucode_size==4096 && !memcmp(a.fp_ucode,ram+0x100,4096),"unterminated source preserves the existing bounded decode window");
    word(ram+0x100,(1u<<24)|(15u<<9)|1u);fp_record_program(&a);CHECK(a.fp_ucode_size==16,"short ended source is bounded precisely");
    printf("FP lifetime: %u checks, %u failures\n",checks,failures);return failures?1:0;
}
