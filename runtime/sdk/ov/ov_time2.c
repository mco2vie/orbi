// nn::time functions MKW imports that totk-pc-recomp does not replace (ov_system.c has the clocks and calendars).
// The host clock is the network clock (ov_system.c answers StandardNetworkSystemClock from it), so it is accurate and
// the network clock never needs a correction from the ntc service.
#include <stdlib.h>
#include <string.h>

#include "host.h"
#include "platform/platform.h"

// bool StandardNetworkSystemClock::IsAccuracySufficient()
static void ov_accuracy(Cpu *c) { ret_x(c, 1); }

// void GetDeviceLocationName(LocationName *out): char[0x24], the host's time zone (plat_time_zone), else UTC
static void ov_location(Cpu *c) {
    char *out = arg_p(c, 0);
    if (!out) return;
    memset(out, 0, 0x24);
    if (!plat_time_zone(out, 0x24)) memcpy(out, "UTC", 3);
    static int logged;
    if (!logged++) rt_log("time: device location %s", out);
}

// Result LoadTimeZoneRule(TimeZoneRule *out, const LocationName &): MKW converts times with ToCalendarTime, which
// ov_system.c answers in host local time without a rule; the rule is left empty.
static void ov_load_rule(Cpu *c) { ret_x(c, 0); }

// AsyncEnsureNetworkClockAvailabilityTask wraps nn::ntc's correction task; its constructor, Initialize and
// GetFinishEvent stay the SDK's (they create and hand out the finish event). StartTask finishes at once: it signals
// that event, and GetResult reports success.
static uint64_t sdk_fn(const char *name) {
    uint64_t a = ldr_symbol(name);
    if (!a) rt_fatal("time: SDK function %s not found", name);
    return a;
}
static void ov_task_start(Cpu *c) {
    static uint64_t finish_event, signal;
    if (!signal) {
        finish_event = sdk_fn("_ZN2nn4time39AsyncEnsureNetworkClockAvailabilityTask14GetFinishEventEv");
        signal = sdk_fn("_ZN2nn2os17SignalSystemEventEPNS0_15SystemEventTypeE");
    }
    uint64_t self = arg_x(c, 0);
    uint64_t ev = rt_call(c, finish_event, 1, self);
    rt_call(c, signal, 1, ev);
    ret_x(c, 0);
}
static void ov_task_result(Cpu *c) { ret_x(c, 0); }

HOST_OVERRIDE("_ZN2nn4time26StandardNetworkSystemClock20IsAccuracySufficientEv", ov_accuracy);
HOST_OVERRIDE("_ZN2nn4time21GetDeviceLocationNameEPNS0_12LocationNameE", ov_location);
HOST_OVERRIDE("_ZN2nn4time16LoadTimeZoneRuleEPNS0_12TimeZoneRuleERKNS0_12LocationNameE", ov_load_rule);
HOST_OVERRIDE("_ZN2nn4time39AsyncEnsureNetworkClockAvailabilityTask9StartTaskEv", ov_task_start);
HOST_OVERRIDE("_ZN2nn4time39AsyncEnsureNetworkClockAvailabilityTask9GetResultEv", ov_task_result);

// ---- the C and C++ clocks (Orbitals: libc++'s std::chrono::steady_clock::now threw a system_error, its
// clock_gettime having failed in the SDK's musl, port-step1q). From the host's clocks: CLOCK_REALTIME (0) the wall
// clock, every other id (MONOTONIC 1, BOOTTIME 7...) the monotonic one. musl's timespec and timeval are two int64s.
static void ov_clock_gettime(Cpu *c) {
    int64_t *ts = arg_p(c, 1);
    if (!ts) { ret_x(c, (uint64_t)-1); return; }
    uint64_t ns = (int32_t)arg_x(c, 0) == 0 ? plat_unix_time_ns() : plat_now_ns();
    ts[0] = (int64_t)(ns / 1000000000u), ts[1] = (int64_t)(ns % 1000000000u);
    ret_x(c, 0);
}
static void ov_gettimeofday(Cpu *c) {   // int gettimeofday(struct timeval *, void *tz)
    int64_t *tv = arg_p(c, 0);
    uint64_t ns = plat_unix_time_ns();
    if (tv) tv[0] = (int64_t)(ns / 1000000000u), tv[1] = (int64_t)(ns % 1000000000u / 1000u);
    ret_x(c, 0);
}
static void ov_time(Cpu *c) {   // time_t time(time_t *)
    int64_t *t = arg_p(c, 0), s = (int64_t)(plat_unix_time_ns() / 1000000000u);
    if (t) *t = s;
    ret_x(c, (uint64_t)s);
}
// steady_clock::time_point steady_clock::now(): nanoseconds; system_clock::now(): microseconds since 1970 (libc++'s
// system_clock duration, as its to_time_t import's mangled name says)
static void ov_steady_now(Cpu *c) { ret_x(c, plat_now_ns()); }
static void ov_system_now(Cpu *c) { ret_x(c, plat_unix_time_ns() / 1000u); }
HOST_OVERRIDE("clock_gettime", ov_clock_gettime);
HOST_OVERRIDE("gettimeofday", ov_gettimeofday);
HOST_OVERRIDE("time", ov_time);
HOST_OVERRIDE("_ZNSt3__16chrono12steady_clock3nowEv", ov_steady_now);
HOST_OVERRIDE("_ZNSt3__16chrono12system_clock3nowEv", ov_system_now);