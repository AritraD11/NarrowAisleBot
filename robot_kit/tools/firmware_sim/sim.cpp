// sim.cpp - run robot_mcu.ino against simulated motors and encoders.
//
// The firmware source is compiled unchanged (with the mock Arduino.h next to
// this file). Each motor is a first-order plant with static friction:
//
//     steady state:  pwm = Kff * w + Kstat * sgn(w)      (no motion below Kstat)
//     dynamics:      dw/dt = (w_ss(pwm) - w) / tau
//
// and its encoder produces real quadrature edges that call the sketch's own
// interrupt handlers. Defaults give a plant that needs about 65 % PWM at
// MAX_WHEEL_SPEED, tau = 0.09 s (NarrowAisleBot's measured value).
//
// Two modes:
//
//   ./sim --pty
//       Real time. Prints "PTY /dev/pts/N". Point tools/encoder_logger.py or
//       the ROS bridge at that path and it behaves like a robot on a bench,
//       wheels in the air. Ctrl-C to stop.
//
//   ./sim --script file.txt [--until MS]
//       As fast as possible, for tests. Each script line is
//           <t_ms> <command>                 e.g.  0 <E1>
//           <t0>-<t1>/<every> <command>      e.g.  100-3000/50 <V,2,-1>
//           <t_ms> !encflip <motor>          wire one encoder backwards
//       Every line the firmware prints comes out as "<t_ms> <line>".
//
// Options: --kff X --kstat X --tau X --seed N --noise X (fraction of w)

#include "Arduino.h"
#include "robot_config.h"

#include <fcntl.h>
#include <signal.h>
#include <stdio.h>
#include <termios.h>
#include <time.h>
#include <unistd.h>

#include <deque>
#include <random>
#include <string>
#include <vector>

SimSerial Serial;
void setup();
void loop();

namespace sim {
unsigned long now_us = 0;
int pin_level[64];
int pin_pwm[64];
void (*pin_isr[64])() = {nullptr};
std::deque<uint8_t> rx;
std::string tx_line;
std::vector<std::string> out_lines;
int pty_master = -1;
bool realtime = false;

void serial_write(const uint8_t* b, size_t n) {
  if (pty_master >= 0) {
    ssize_t w = ::write(pty_master, b, n);
    (void)w;
    return;
  }
  for (size_t k = 0; k < n; k++) {
    char c = (char)b[k];
    if (c == '\n') {
      printf("%lu %s\n", now_us / 1000UL, tx_line.c_str());
      tx_line.clear();
    } else if (c != '\r') {
      tx_line += c;
    }
  }
}
int serial_available() { return (int)rx.size(); }
int serial_read() {
  if (rx.empty()) return -1;
  int c = rx.front();
  rx.pop_front();
  return c;
}
}  // namespace sim

struct Plant {
  double w = 0, phi = 0;        // rad/s, rad (true wheel angle)
  long counts = 0;              // firmware counts produced so far (wheel sense)
  int gray = 0;                 // index into the Gray sequence
  double kff, kstat, tau;
  int enc_flip = 1;             // -1 = wired backwards (fault injection)
};

static const int GRAY[4][2] = {{0, 0}, {1, 0}, {1, 1}, {0, 1}};  // A leads B = forward

static double hw_pwm(int i) {
#if DRIVER_TYPE == DRIVER_PWM_DIR
  double duty = sim::pin_pwm[PIN_A[i]];
  return sim::pin_level[PIN_B[i]] ? -duty : duty;
#elif DRIVER_TYPE == DRIVER_PWM_IN1_IN2
  double duty = sim::pin_pwm[PIN_A[i]];
  int a = sim::pin_level[PIN_B[i]], b = sim::pin_level[PIN_C[i]];
  return (a && !b) ? duty : ((!a && b) ? -duty : 0.0);
#else
  return (double)sim::pin_pwm[PIN_A[i]] - (double)sim::pin_pwm[PIN_B[i]];
#endif
}

static void set_enc_pins(int i, int g) {
  sim::pin_level[ENC_A[i]] = GRAY[g][0];
  sim::pin_level[ENC_B[i]] = GRAY[g][1];
}

static void step_plants(std::vector<Plant>& P, double h, std::mt19937& rng, double noise) {
  std::normal_distribution<double> nd(0.0, 1.0);
  for (int i = 0; i < NUM_MOTORS; i++) {
    Plant& p = P[i];
    // Physical motor: the firmware multiplies by MOTOR_DIR before writing the
    // pins, the mounting multiplies by it again. A correct config cancels.
    double u = hw_pwm(i) * MOTOR_DIR[i];
    double au = fabs(u);
    double w_ss = 0;
    if (au > p.kstat) w_ss = (au - p.kstat) / p.kff * (u > 0 ? 1 : -1);
    if (fabs(p.w) < 1e-3 && au <= p.kstat) p.w = 0;      // static friction holds it
    else p.w += (w_ss - p.w) * (h / p.tau);
    double w_meas = p.w * (1.0 + noise * nd(rng));
    p.phi += w_meas * h;

    // Encoder: firmware counts in wheel sense = floor(phi * CPR / 2pi).
    long target = (long)floor(p.phi * ENCODER_CPR[i] / (2.0 * PI));
    int per_count = (ENCODER_DECODING == 4) ? 1 : 2;     // Gray transitions per count
    while (p.counts != target) {
      int dir = target > p.counts ? 1 : -1;
      // Electrical direction seen by the MCU = wheel sense * ENC_DIR * fault.
      int edir = dir * ENC_DIR[i] * p.enc_flip;
      for (int k = 0; k < per_count; k++) {
        int old = p.gray;
        p.gray = (p.gray + (edir > 0 ? 1 : 3)) % 4;
        set_enc_pins(i, p.gray);
        int changed = (GRAY[old][0] != GRAY[p.gray][0]) ? ENC_A[i] : ENC_B[i];
        if (sim::pin_isr[changed]) sim::pin_isr[changed]();
      }
      p.counts += dir;
    }
  }
}

struct ScriptCmd { unsigned long t0, t1, every; std::string cmd; };

static std::vector<ScriptCmd> load_script(const char* path) {
  std::vector<ScriptCmd> out;
  FILE* f = fopen(path, "r");
  if (!f) { perror(path); exit(2); }
  char line[512];
  while (fgets(line, sizeof line, f)) {
    std::string s(line);
    while (!s.empty() && (s.back() == '\n' || s.back() == '\r' || s.back() == ' ')) s.pop_back();
    if (s.empty() || s[0] == '#') continue;
    size_t sp = s.find(' ');
    if (sp == std::string::npos) continue;
    std::string when = s.substr(0, sp), cmd = s.substr(sp + 1);
    ScriptCmd c{0, 0, 0, cmd};
    size_t dash = when.find('-'), slash = when.find('/');
    if (dash != std::string::npos && slash != std::string::npos) {
      c.t0 = strtoul(when.c_str(), nullptr, 10);
      c.t1 = strtoul(when.c_str() + dash + 1, nullptr, 10);
      c.every = strtoul(when.c_str() + slash + 1, nullptr, 10);
    } else {
      c.t0 = c.t1 = strtoul(when.c_str(), nullptr, 10);
    }
    out.push_back(c);
  }
  fclose(f);
  return out;
}

static volatile bool g_stop = false;
static void on_sig(int) { g_stop = true; }

static double mono_s() {
  timespec ts;
  clock_gettime(CLOCK_MONOTONIC, &ts);
  return ts.tv_sec + ts.tv_nsec * 1e-9;
}

int main(int argc, char** argv) {
  const char* script = nullptr;
  bool pty = false;
  unsigned long until_ms = 10000;
  double kff = -1, kstat = -1, tau = 0.09, noise = 0.003;
  unsigned seed = 1;
  for (int a = 1; a < argc; a++) {
    std::string k = argv[a];
    auto next = [&]() { return a + 1 < argc ? argv[++a] : (char*)"0"; };
    if (k == "--pty") pty = true;
    else if (k == "--script") script = next();
    else if (k == "--until") until_ms = strtoul(next(), nullptr, 10);
    else if (k == "--kff") kff = atof(next());
    else if (k == "--kstat") kstat = atof(next());
    else if (k == "--tau") tau = atof(next());
    else if (k == "--noise") noise = atof(next());
    else if (k == "--seed") seed = (unsigned)atoi(next());
    else { fprintf(stderr, "unknown option %s\n", k.c_str()); return 2; }
  }
  if (!pty && !script) {
    fprintf(stderr, "usage: sim --pty | --script FILE [--until MS]\n");
    return 2;
  }
  if (kff < 0) kff = 0.65 * PWM_MAX / MAX_WHEEL_SPEED;
  if (kstat < 0) kstat = 0.03 * PWM_MAX;

  std::mt19937 rng(seed);
  std::vector<Plant> P(NUM_MOTORS);
  for (int i = 0; i < NUM_MOTORS; i++) {
    double spread = 1.0 + 0.03 * ((i % 3) - 1);       // motors differ by a few percent
    P[i].kff = kff * spread;
    P[i].kstat = kstat;
    P[i].tau = tau;
    set_enc_pins(i, 0);
  }
  for (int i = 0; i < 64; i++) sim::pin_pwm[i] = 0;

  if (pty) {
    sim::pty_master = posix_openpt(O_RDWR | O_NOCTTY);
    if (sim::pty_master < 0 || grantpt(sim::pty_master) || unlockpt(sim::pty_master)) {
      perror("pty");
      return 1;
    }
    const char* name = ptsname(sim::pty_master);
    int slave = open(name, O_RDWR | O_NOCTTY);      // held open: no hangup when a client leaves
    termios t;
    tcgetattr(slave, &t);
    cfmakeraw(&t);
    tcsetattr(slave, TCSANOW, &t);
    fcntl(sim::pty_master, F_SETFL, fcntl(sim::pty_master, F_GETFL) | O_NONBLOCK);
    printf("PTY %s\n", name);
    printf("#PLANT kff=%.3f kstat=%.3f tau=%.3f motors=%d (motor i kff x 0.97/1.00/1.03)\n",
           kff, kstat, tau, NUM_MOTORS);
    fflush(stdout);
    signal(SIGINT, on_sig);
    signal(SIGTERM, on_sig);
    sim::realtime = true;
  } else {
    printf("#PLANT kff=%.3f kstat=%.3f tau=%.3f motors=%d\n", kff, kstat, tau, NUM_MOTORS);
  }

  std::vector<ScriptCmd> cmds;
  std::vector<unsigned long> next_due;
  if (script) {
    cmds = load_script(script);
    for (auto& c : cmds) next_due.push_back(c.t0);
  }

  const unsigned long H_US = 50;
  const double t_start = mono_s();
  setup();
  while (!g_stop) {
    unsigned long ms = sim::now_us / 1000UL;
    if (script) {
      if (ms >= until_ms) break;
      for (size_t k = 0; k < cmds.size(); k++) {
        ScriptCmd& c = cmds[k];
        if (next_due[k] == (unsigned long)-1 || ms < next_due[k]) continue;
        if (c.cmd.rfind("!encflip", 0) == 0) {
          int m = atoi(c.cmd.c_str() + 9);
          if (m >= 0 && m < NUM_MOTORS) P[m].enc_flip = -P[m].enc_flip;
        } else {
          for (char ch : c.cmd) sim::rx.push_back((uint8_t)ch);
        }
        if (c.every && next_due[k] + c.every <= c.t1) next_due[k] += c.every;
        else next_due[k] = (unsigned long)-1;
      }
    } else {
      uint8_t buf[256];
      ssize_t n = ::read(sim::pty_master, buf, sizeof buf);
      for (ssize_t k = 0; k < n; k++) sim::rx.push_back(buf[k]);
      // Keep pace with the wall clock.
      double ahead = sim::now_us * 1e-6 - (mono_s() - t_start);
      if (ahead > 0.002) usleep((useconds_t)(ahead * 1e6));
    }
    step_plants(P, H_US * 1e-6, rng, noise);
    loop();
    sim::now_us += H_US;
  }
  return 0;
}
