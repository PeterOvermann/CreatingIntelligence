#	creatingintelligence.org
#	Makefile
#   - memory (CLI)
# 	- memorytest (performance and capacity testing)
	
CC = gcc
CFLAGS = -Wall -Wextra -O3


MAKEFILE_DIR := $(dir $(abspath $(lastword $(MAKEFILE_LIST))))
BIN_DIR := $(MAKEFILE_DIR)build

CLI_TARGET = $(BIN_DIR)/memory
TEST_TARGET = $(BIN_DIR)/memorytest

.PHONY: all clean directories

all: directories $(CLI_TARGET) $(TEST_TARGET)

directories:
	@mkdir -p $(BIN_DIR)

$(CLI_TARGET): commandline.c memory.c
	$(CC) $(CFLAGS) -o $@ $^ -lm

$(TEST_TARGET): testing.c memory.c
	$(CC) $(CFLAGS) -o $@ $^ -lm
	
clean:
	rm -rf $(BIN_DIR)
