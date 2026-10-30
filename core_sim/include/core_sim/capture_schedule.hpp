// Copyright (C) 2026. MIT License.
#pragma once
#include <cstdint>

namespace microsoft { namespace projectairsim {
// Simulation-time deadlines. Skip missed deadlines without drift or catch-up
// bursts; a repeated timestamp never produces another capture. Reset per scene.
class CaptureSchedule {
 public:
  bool Due(int64_t now, int64_t interval) {
    if (interval <= 0) interval = 1;
    if (now < last_time_ || interval != interval_) {
      next_ = interval;
      interval_ = interval;
    }
    last_time_ = now;
    if (now < next_) return false;
    next_ += ((now - next_) / interval + 1) * interval;
    return true;
  }
 private:
  int64_t next_ = 0;
  int64_t interval_ = 0;
  int64_t last_time_ = 0;
};
}}
