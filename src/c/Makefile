
#	creatingintelligence.org
#	Makefile
#   - memory (CLI)
# 	- memorytest (performance and capacity testing)
# 	- libmemory (used by Python frontend)
	
CC = gcc
CFLAGS = -Wall -Wextra -O3 -fPIC
LDFLAGS = -shared

UNAME_S := $(shell uname -s)
ifeq ($(UNAME_S),Darwin)
    EXT = dylib
else
    EXT = so
endif

REPO_ROOT = ../..
BIN_DIR = $(REPO_ROOT)/bin
LIB_DIR = $(REPO_ROOT)/lib

LIB_TARGET = $(LIB_DIR)/libmemory.$(EXT)
CLI_TARGET = $(BIN_DIR)/memory
TEST_TARGET = $(BIN_DIR)/memorytest

.PHONY: all clean directories

all: directories $(LIB_TARGET) $(CLI_TARGET) $(TEST_TARGET)

directories:
	mkdir -p $(BIN_DIR) $(LIB_DIR)

$(LIB_TARGET): memory.c
	$(CC) $(CFLAGS) $(LDFLAGS) -o $@ $<

$(CLI_TARGET): commandline.c memory.c
	$(CC) $(CFLAGS) -o $@ $^

$(TEST_TARGET): testing.c memory.c
	$(CC) $(CFLAGS) -o $@ $^

clean:
	rm -f $(LIB_TARGET) $(CLI_TARGET) $(TEST_TARGET)
