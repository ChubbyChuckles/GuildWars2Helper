#include "render.h"

#include "../utils/utils.h"

#include <stdlib.h>
#include <string.h>

#ifdef _WIN32
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#endif

#include <GLFW/glfw3.h>

#ifdef __APPLE__
#include <OpenGL/gl.h>
#else
#include <GL/gl.h>
#endif

#include "../gui/nk_config.h"

#define NK_GLFW_GL2_IMPLEMENTATION
#include "nuklear_glfw_gl2.h"

#define MAX_VERTEX_BUFFER 512 * 1024
#define MAX_ELEMENT_BUFFER 128 * 1024

static struct nk_glfw *backend_driver(struct render_backend *backend)
{
    return (struct nk_glfw *)backend->driver;
}

static void apply_default_theme(struct nk_context *ctx)
{
    struct nk_color table[NK_COLOR_COUNT];
    table[NK_COLOR_TEXT] = nk_rgba(211, 255, 246, 255);
    table[NK_COLOR_WINDOW] = nk_rgba(12, 14, 24, 240);
    table[NK_COLOR_HEADER] = nk_rgba(22, 26, 46, 255);
    table[NK_COLOR_BORDER] = nk_rgba(36, 48, 74, 255);
    table[NK_COLOR_BUTTON] = nk_rgba(32, 64, 96, 255);
    table[NK_COLOR_BUTTON_HOVER] = nk_rgba(64, 128, 192, 255);
    table[NK_COLOR_BUTTON_ACTIVE] = nk_rgba(128, 224, 255, 255);
    table[NK_COLOR_TOGGLE] = nk_rgba(32, 64, 96, 255);
    table[NK_COLOR_TOGGLE_HOVER] = nk_rgba(64, 128, 192, 255);
    table[NK_COLOR_TOGGLE_CURSOR] = nk_rgba(128, 224, 255, 255);
    table[NK_COLOR_SELECT] = nk_rgba(64, 128, 192, 255);
    table[NK_COLOR_SELECT_ACTIVE] = nk_rgba(128, 224, 255, 255);
    table[NK_COLOR_SLIDER] = nk_rgba(32, 64, 96, 255);
    table[NK_COLOR_SLIDER_CURSOR] = nk_rgba(128, 224, 255, 255);
    table[NK_COLOR_SLIDER_CURSOR_HOVER] = nk_rgba(160, 240, 255, 255);
    table[NK_COLOR_SLIDER_CURSOR_ACTIVE] = nk_rgba(192, 255, 255, 255);
    table[NK_COLOR_PROPERTY] = nk_rgba(24, 32, 56, 255);
    table[NK_COLOR_EDIT] = nk_rgba(24, 32, 56, 255);
    table[NK_COLOR_EDIT_CURSOR] = nk_rgba(192, 255, 255, 255);
    table[NK_COLOR_COMBO] = nk_rgba(24, 32, 56, 255);
    table[NK_COLOR_CHART] = nk_rgba(24, 32, 56, 255);
    table[NK_COLOR_CHART_COLOR] = nk_rgba(128, 224, 255, 255);
    table[NK_COLOR_CHART_COLOR_HIGHLIGHT] = nk_rgba(192, 255, 255, 255);
    table[NK_COLOR_SCROLLBAR] = nk_rgba(24, 32, 56, 255);
    table[NK_COLOR_SCROLLBAR_CURSOR] = nk_rgba(64, 128, 192, 255);
    table[NK_COLOR_SCROLLBAR_CURSOR_HOVER] = nk_rgba(128, 224, 255, 255);
    table[NK_COLOR_SCROLLBAR_CURSOR_ACTIVE] = nk_rgba(192, 255, 255, 255);
    table[NK_COLOR_TAB_HEADER] = nk_rgba(22, 26, 46, 255);
    nk_style_from_table(ctx, table);
}

static void log_error(struct log_context *logger, const char *message)
{
    if (logger != NULL)
    {
        log_message(logger, LOG_LEVEL_ERROR, "%s", message);
    }
}

int render_init(struct render_backend *backend,
                const struct render_backend_config *config)
{
    if (backend == NULL || config == NULL)
    {
        return -1;
    }

    memset(backend, 0, sizeof(*backend));
    backend->logger = config->logger;
    backend->width = config->width;
    backend->height = config->height;

    if (!glfwInit())
    {
        log_error(config->logger, "Failed to initialize GLFW.");
        return -1;
    }

    glfwWindowHint(GLFW_CONTEXT_VERSION_MAJOR, 2);
    glfwWindowHint(GLFW_CONTEXT_VERSION_MINOR, 0);
    glfwWindowHint(GLFW_VISIBLE, GLFW_TRUE);
    glfwWindowHint(GLFW_RESIZABLE, GLFW_TRUE);

    GLFWwindow *window = glfwCreateWindow(config->width,
                                          config->height,
                                          config->title,
                                          NULL,
                                          NULL);
    if (window == NULL)
    {
        log_error(config->logger, "Failed to create GLFW window.");
        glfwTerminate();
        return -1;
    }

    glfwMakeContextCurrent(window);
    glfwSwapInterval(1);

    struct nk_glfw *driver = malloc(sizeof(*driver));
    if (driver == NULL)
    {
        log_error(config->logger, "Failed to allocate Nuklear driver state.");
        glfwDestroyWindow(window);
        glfwTerminate();
        return -1;
    }

    memset(driver, 0, sizeof(*driver));
    backend->nk = nk_glfw3_init(driver, window, NK_GLFW3_INSTALL_CALLBACKS);
    if (backend->nk == NULL)
    {
        log_error(config->logger, "Failed to initialize Nuklear GLFW bridge.");
        free(driver);
        glfwDestroyWindow(window);
        glfwTerminate();
        return -1;
    }

    struct nk_font_atlas *atlas = NULL;
    nk_glfw3_font_stash_begin(driver, &atlas);

    struct nk_font_config font_cfg = nk_font_config(0);
    font_cfg.oversample_h = 2;
    font_cfg.oversample_v = 1;

    const char *font_path = "assets/Orbitron-Regular.ttf";
    struct nk_font *font = nk_font_atlas_add_from_file(atlas,
                                                       font_path,
                                                       20.0f,
                                                       &font_cfg);
    nk_glfw3_font_stash_end(driver);

    if (font != NULL)
    {
        nk_style_set_font(backend->nk, &font->handle);
    }
    else
    {
        log_message(config->logger,
                    LOG_LEVEL_WARN,
                    "Using default font. Could not load %s.",
                    font_path);
    }

    apply_default_theme(backend->nk);

    backend->window = window;
    backend->driver = driver;

    return 0;
}

void render_shutdown(struct render_backend *backend)
{
    if (backend == NULL)
    {
        return;
    }

    if (backend->driver != NULL)
    {
        nk_glfw3_shutdown(backend_driver(backend));
        free(backend->driver);
        backend->driver = NULL;
    }

    if (backend->window != NULL)
    {
        glfwDestroyWindow((GLFWwindow *)backend->window);
        backend->window = NULL;
    }

    glfwTerminate();
}

void render_poll_events(struct render_backend *backend)
{
    (void)backend;
    glfwPollEvents();
}

void render_begin_frame(struct render_backend *backend)
{
    if (backend == NULL || backend->driver == NULL)
    {
        return;
    }

    nk_glfw3_new_frame(backend_driver(backend));
}

void render_end_frame(struct render_backend *backend)
{
    if (backend == NULL || backend->driver == NULL)
    {
        return;
    }

    int width = 0;
    int height = 0;
    glfwGetFramebufferSize((GLFWwindow *)backend->window, &width, &height);
    backend->width = width;
    backend->height = height;

    glViewport(0, 0, width, height);
    glClearColor(0.04f, 0.05f, 0.09f, 1.0f);
    glClear(GL_COLOR_BUFFER_BIT);

    nk_glfw3_render(backend_driver(backend),
                    NK_ANTI_ALIASING_ON,
                    MAX_VERTEX_BUFFER,
                    MAX_ELEMENT_BUFFER);

    glfwSwapBuffers((GLFWwindow *)backend->window);
}

bool render_should_close(const struct render_backend *backend)
{
    if (backend == NULL || backend->window == NULL)
    {
        return true;
    }

    return glfwWindowShouldClose((GLFWwindow *)backend->window) != 0;
}

struct nk_context *render_context(struct render_backend *backend)
{
    if (backend == NULL)
    {
        return NULL;
    }

    return backend->nk;
}

float render_time_seconds(void)
{
    return (float)glfwGetTime();
}
