#pragma once
// ArduPlane JSON simulator transport. Physics owns all calls; no renderer/RPC writes.
#ifdef _WIN32
#ifndef NOMINMAX
#define NOMINMAX
#endif
#include <winsock2.h>
#include <ws2tcpip.h>
#else
#include <sys/socket.h>
#include <sys/select.h>
#include <arpa/inet.h>
#include <unistd.h>
#endif
#include <array>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <stdexcept>
#include <string>
#include "json.hpp"

namespace microsoft { namespace projectairsim {
class TiguarJsonBridge {
 public:
  TiguarJsonBridge(const std::string& bind_host, int port, int timeout_ms)
      : timeout_ms_(timeout_ms) {
#ifdef _WIN32
    WSADATA wsa{}; if (WSAStartup(MAKEWORD(2,2), &wsa)) throw std::runtime_error("WSAStartup failed");
#endif
    socket_ = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP);
    if (socket_ == invalid_socket) throw std::runtime_error("Cannot create SITL socket");
    sockaddr_in address{}; address.sin_family=AF_INET; address.sin_port=htons(static_cast<uint16_t>(port));
    if (inet_pton(AF_INET,bind_host.c_str(),&address.sin_addr)!=1 ||
        bind(socket_,reinterpret_cast<sockaddr*>(&address),sizeof(address))) {
      Close(); throw std::runtime_error("Cannot bind SITL endpoint " + bind_host + ":" + std::to_string(port));
    }
  }
  ~TiguarJsonBridge() { Close(); }
  TiguarJsonBridge(const TiguarJsonBridge&)=delete;
  TiguarJsonBridge& operator=(const TiguarJsonBridge&)=delete;
  const std::array<uint16_t,16>& Pwm() const {return pwm_;}
  bool Receive() {
    const auto deadline=std::chrono::steady_clock::now()+std::chrono::milliseconds(timeout_ms_);
    while (std::chrono::steady_clock::now()<deadline) {
      fd_set read_set; FD_ZERO(&read_set); FD_SET(socket_,&read_set);
      timeval timeout{0,10000};
      if (select(static_cast<int>(socket_)+1,&read_set,nullptr,nullptr,&timeout)<=0) continue;
      std::array<unsigned char,80> bytes{}; sockaddr_in sender{};
#ifdef _WIN32
      int length=sizeof(sender);
#else
      socklen_t length=sizeof(sender);
#endif
      const int count=recvfrom(socket_,reinterpret_cast<char*>(bytes.data()),static_cast<int>(bytes.size()),0,reinterpret_cast<sockaddr*>(&sender),&length);
      if (count!=40) continue; // Pinned configuration uses 16 outputs.
      uint16_t magic=0,rate=0; uint32_t frame=0;
      std::memcpy(&magic,bytes.data(),2); std::memcpy(&rate,bytes.data()+2,2); std::memcpy(&frame,bytes.data()+4,4);
      if (magic!=18458 || rate!=250) continue;
      if (have_peer_ && (sender.sin_addr.s_addr!=peer_.sin_addr.s_addr || sender.sin_port!=peer_.sin_port)) continue;
      if (have_frame_ && frame==frame_) { if (!last_sensor_.empty()) SendRaw(last_sensor_); continue; }
      if (have_frame_ && frame<frame_) {error_="SITL frame counter reset";return false;}
      if (have_frame_ && frame!=frame_+1) {error_="SITL frame sequence gap";return false;}
      peer_=sender;have_peer_=true;frame_=frame;have_frame_=true;
      std::memcpy(pwm_.data(),bytes.data()+8,32);
      return true;
    }
    error_="SITL exchange timed out";return false;
  }
  void Send(const nlohmann::json& state) {
    last_sensor_="\n"+state.dump()+"\n";SendRaw(last_sensor_);
  }
  const std::string& Error() const {return error_;}
 private:
  void SendRaw(const std::string& text) {
    if (have_peer_) sendto(socket_,text.data(),static_cast<int>(text.size()),0,reinterpret_cast<sockaddr*>(&peer_),sizeof(peer_));
  }
  void Close() {
    if (socket_!=invalid_socket) {
#ifdef _WIN32
      closesocket(socket_);WSACleanup();
#else
      close(socket_);
#endif
      socket_=invalid_socket;
    }
  }
#ifdef _WIN32
  using Socket=SOCKET;static constexpr Socket invalid_socket=INVALID_SOCKET;
#else
  using Socket=int;static constexpr Socket invalid_socket=-1;
#endif
  Socket socket_=invalid_socket;
  sockaddr_in peer_{};bool have_peer_=false,have_frame_=false;
  uint32_t frame_=0;int timeout_ms_=1000;
  std::array<uint16_t,16> pwm_{};
  std::string last_sensor_,error_;
};
}}
