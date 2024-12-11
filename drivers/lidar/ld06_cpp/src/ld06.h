#pragma once
#include <functional>
#include <inttypes.h>
#include <stddef.h>
#include <array>
#define POINT_PER_PACK 12 
#define HEADER 0x54 
#define LD06_NB_POINTS 500

typedef struct  __attribute__((packed)) { 
uint16_t distance; 
uint8_t intensity; 
} LidarPointStructDef; 


typedef struct  __attribute__((packed)) { 
uint8_t           header; 
uint8_t           ver_len; 
uint16_t          speed; 
uint16_t          start_angle; 
LidarPointStructDef point[POINT_PER_PACK]; 
uint16_t          end_angle; 
uint16_t          timestamp; 
uint8_t           crc8; 
}LiDARFrameTypeDef;


typedef struct  
{
    uint16_t distance; 
    uint8_t intensity; 
    double angle;
}Point;



enum RxState{
    PERDU,
    ATTENTE_LEN,
    RX_DATA
};


class LD06
{
private:
    LiDARFrameTypeDef lidar_packet;
    std::array<Point,LD06_NB_POINTS> points;
    size_t nb_points;
    size_t packet_index;
    RxState rx_state;
    std::function<void(std::array<Point,LD06_NB_POINTS>, size_t)> callback;
    
    void handle_data();

public:
    LD06(std::function<void(std::array<Point,LD06_NB_POINTS>, size_t)> callback);


    int feed(uint8_t* buffer, size_t len);
};

