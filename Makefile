PROJECT := gw2helper
BUILD_DIR := build
BIN_DIR := $(BUILD_DIR)/bin
OBJ_DIR := $(BUILD_DIR)/obj
TEST_OBJ_DIR := $(BUILD_DIR)/tests
DEPS_DIR := scripts/deps
GLFW_DIR ?= $(DEPS_DIR)/glfw
GLFW_BUILD_DIR ?= $(GLFW_DIR)/build
GLFW_SRC_DIR := $(GLFW_BUILD_DIR)/src
GLFW_LIB_RELEASE := $(GLFW_SRC_DIR)/Release

CC ?= gcc
CFLAGS ?= -std=c99 -Wall -Wextra -pedantic
CFLAGS += -Iinclude -Isrc -Isrc/gui -Isrc/render -Isrc/utils
CFLAGS += -I$(GLFW_DIR)/include

SRC_FILES := $(wildcard src/*.c) \
             $(wildcard src/gui/*.c) \
             $(wildcard src/render/*.c) \
             $(wildcard src/utils/*.c)
OBJ_FILES := $(patsubst src/%.c,$(OBJ_DIR)/%.o,$(SRC_FILES))

TEST_SRC := $(wildcard tests/*.c)
TEST_OBJS := $(patsubst tests/%.c,$(TEST_OBJ_DIR)/%.o,$(TEST_SRC))
TEST_BIN := $(BIN_DIR)/tests

ifeq ($(OS),Windows_NT)
	EXE := $(BIN_DIR)/$(PROJECT).exe
	GLFW_LIB_NAME := glfw3.lib
	GLFW_LINK_DIRS := -L$(GLFW_SRC_DIR) -L$(GLFW_LIB_RELEASE)
	GLFW_LINK := $(GLFW_LINK_DIRS) -lglfw3 -lopengl32 -lgdi32 -lshell32 -luser32
	MKDIR_P = mkdir -p $(1)
	RM_RF = rm -rf $(1)
	FETCH_GLFW := pwsh scripts/fetch_glfw.ps1
	FETCH_NUKLEAR := pwsh scripts/fetch_nuklear.ps1
else
	EXE := $(BIN_DIR)/$(PROJECT)
	GLFW_LIB_NAME := libglfw3.a
	UNAME_S := $(shell uname -s)
	GLFW_LINK_DIRS := -L$(GLFW_SRC_DIR)
	GLFW_LINK := $(GLFW_LINK_DIRS) -lglfw3 -lm -ldl -lpthread
	ifeq ($(UNAME_S),Darwin)
		GLFW_LINK += -framework Cocoa -framework IOKit -framework CoreVideo -framework OpenGL
	else
		GLFW_LINK += -lGL
	endif
	MKDIR_P = mkdir -p $(1)
	RM_RF = rm -rf $(1)
	FETCH_GLFW := bash scripts/fetch_glfw.sh
	FETCH_NUKLEAR := bash scripts/fetch_nuklear.sh
endif

.PHONY: all clean run test deps

all: $(EXE)

run: $(EXE)
	$(EXE)

$(EXE): deps $(OBJ_FILES)
	$(call MKDIR_P,$(BIN_DIR))
	$(CC) $(OBJ_FILES) $(GLFW_LINK) -o $@

$(OBJ_DIR)/%.o: src/%.c | deps
	$(call MKDIR_P,$(dir $@))
	$(CC) $(CFLAGS) -c $< -o $@

$(TEST_OBJ_DIR)/%.o: tests/%.c
	$(call MKDIR_P,$(dir $@))
	$(CC) $(CFLAGS) -Isrc -Itests -c $< -o $@

$(TEST_BIN): $(TEST_OBJS) $(OBJ_DIR)/utils/utils.o
	$(call MKDIR_P,$(BIN_DIR))
	$(CC) $(filter %.o,$^) -o $@

clean:
	$(call RM_RF,$(BUILD_DIR))

deps:
	@if [ ! -d $(GLFW_DIR) ]; then \
		$(FETCH_GLFW); \
	fi
	@if [ ! -d $(GLFW_BUILD_DIR) ]; then \
		cmake -S $(GLFW_DIR) -B $(GLFW_BUILD_DIR) -DBUILD_SHARED_LIBS=OFF \
			-DGLFW_BUILD_EXAMPLES=OFF -DGLFW_BUILD_TESTS=OFF -DGLFW_BUILD_DOCS=OFF; \
	fi
	@if [ ! -f $(GLFW_SRC_DIR)/$(GLFW_LIB_NAME) ] && \
		[ ! -f $(GLFW_LIB_RELEASE)/$(GLFW_LIB_NAME) ]; then \
		cmake --build $(GLFW_BUILD_DIR) --config Release; \
	fi
	@if [ ! -f include/nuklear.h ] || [ ! -f include/nuklear_glfw_gl2.h ]; then \
		$(FETCH_NUKLEAR); \
	fi
	@if [ ! -f include/nuklear.h ] || [ ! -f include/nuklear_glfw_gl2.h ]; then \
		echo "Error: Nuklear headers missing. Please download nuklear.h and nuklear_glfw_gl2.h from https://github.com/Immediate-Mode-UI/Nuklear and place them under include/."; \
		exit 1; \
	fi

test: $(TEST_BIN)
	$(TEST_BIN)
