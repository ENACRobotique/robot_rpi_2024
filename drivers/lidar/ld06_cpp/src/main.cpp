#include <ecal/ecal.h>
#include <ecal/msg/protobuf/publisher.h>
#include <unistd.h>
#include <inttypes.h>
#include <iostream>
#include <thread>

#include "ld06.h"
#include "lidar_data.pb.h"


#include <fcntl.h> // Contains file controls like O_RDWR
#include <errno.h> // Error integer and strerror() function
#include <termios.h> // Contains POSIX terminal control definitions
#include <unistd.h> // write(), read(), close()

#define SERIAL_BUF_LEN 47

int init_serial(int serial_port) {
    // Create new termios struct, we call it 'tty' for convention
  struct termios tty;

  // Read in existing settings, and handle any error
  if(tcgetattr(serial_port, &tty) != 0) {
      printf("Error %i from tcgetattr: %s\n", errno, strerror(errno));
      return 1;
  }

  tty.c_cflag &= ~PARENB; // Clear parity bit, disabling parity (most common)
  tty.c_cflag &= ~CSTOPB; // Clear stop field, only one stop bit used in communication (most common)
  tty.c_cflag &= ~CSIZE; // Clear all bits that set the data size 
  tty.c_cflag |= CS8; // 8 bits per byte (most common)
  tty.c_cflag &= ~CRTSCTS; // Disable RTS/CTS hardware flow control (most common)
  tty.c_cflag |= CREAD | CLOCAL; // Turn on READ & ignore ctrl lines (CLOCAL = 1)

  tty.c_lflag &= ~ICANON;
  tty.c_lflag &= ~ECHO; // Disable echo
  tty.c_lflag &= ~ECHOE; // Disable erasure
  tty.c_lflag &= ~ECHONL; // Disable new-line echo
  tty.c_lflag &= ~ISIG; // Disable interpretation of INTR, QUIT and SUSP
  tty.c_iflag &= ~(IXON | IXOFF | IXANY); // Turn off s/w flow ctrl
  tty.c_iflag &= ~(IGNBRK|BRKINT|PARMRK|ISTRIP|INLCR|IGNCR|ICRNL); // Disable any special handling of received bytes

  tty.c_oflag &= ~OPOST; // Prevent special interpretation of output bytes (e.g. newline chars)
  tty.c_oflag &= ~ONLCR; // Prevent conversion of newline to carriage return/line feed
  // tty.c_oflag &= ~OXTABS; // Prevent conversion of tabs to spaces (NOT PRESENT ON LINUX)
  // tty.c_oflag &= ~ONOEOT; // Prevent removal of C-d chars (0x004) in output (NOT PRESENT ON LINUX)

  tty.c_cc[VTIME] = 10;    // Wait for up to 1s (10 deciseconds), returning as soon as any data is received.
  tty.c_cc[VMIN] = 0;

  // Set in/out baud rate to be 9600
  cfsetispeed(&tty, B230400);
  cfsetospeed(&tty, B230400);

  // Save tty settings, also checking for error
  if (tcsetattr(serial_port, TCSANOW, &tty) != 0) {
      printf("Error %i from tcsetattr: %s\n", errno, strerror(errno));
      return 1;
  }
  return 0;
}

int main(int argc, char** argv){

  if(argc < 2) {
    std::cout << "Please specify serial port" << std::endl;
    return -1;
  }
  
  int serial_port = open(argv[1], O_RDWR);

  if(init_serial(serial_port)) {
    std::cout << "Error configuring serial port!" << std::endl;
  }

  
  // Initialize eCAL and create a protobuf publisher
  eCAL::Initialize(argc, argv, "ld06_driver");
  eCAL::protobuf::CPublisher<enac::Lidar> publisher("lidar_data");


  LD06 ld06([&publisher](std::array<Point,LD06_NB_POINTS> points, size_t len){
    enac::Lidar lidar_msg;
    for (int i=0; i<len; i++){
        lidar_msg.add_angles(360-points[i].angle);
        lidar_msg.add_distances(points[i].distance);
        lidar_msg.add_quality(points[i].intensity);
    }
    // Send the message
    publisher.Send(lidar_msg);

  });


  // Infinite loop (using eCAL::Ok() will enable us to gracefully shutdown the
  // Process from another application)
  while (eCAL::Ok()){
    uint8_t cs[SERIAL_BUF_LEN];

    int num_bytes = read(serial_port, cs, SERIAL_BUF_LEN);
    ld06.feed(cs, num_bytes);
  }

  // finalize eCAL API
  eCAL::Finalize();
}
