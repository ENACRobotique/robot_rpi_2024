cmake_minimum_required(VERSION 3.0)
set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)

project(ld06_driver)

set(CMAKE_CXX_STANDARD 14)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(eCAL REQUIRED)
find_package(Protobuf REQUIRED)

set(source_files
  src/main.cpp
  src/ld06.cpp
)

set(PROTO_DIR  ${CMAKE_CURRENT_SOURCE_DIR}/../../../proto)

set(protobuf_files
	${PROTO_DIR}/lidar_data.proto
)


add_executable(${PROJECT_NAME} ${source_files})

PROTOBUF_TARGET_CPP(${PROJECT_NAME} ${PROTO_DIR} ${protobuf_files})

target_link_libraries(${PROJECT_NAME}
  eCAL::core
  protobuf::libprotobuf
)
