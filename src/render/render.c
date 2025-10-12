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
    glfwWindowHint(GLFW_DECORATED, GLFW_FALSE);

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

    backend->nk = nk_glfw3_init(window, NK_GLFW3_INSTALL_CALLBACKS);
    if (backend->nk == NULL)
    {
        log_error(config->logger, "Failed to initialize Nuklear GLFW bridge.");
        glfwDestroyWindow(window);
        glfwTerminate();
        return -1;
    }

    struct nk_font_atlas *atlas = NULL;
    nk_glfw3_font_stash_begin(&atlas);

    struct nk_font_config font_cfg = nk_font_config(0);
    font_cfg.oversample_h = 2;
    font_cfg.oversample_v = 1;

    const char *font_path = "assets/Orbitron-VariableFont_wght.ttf";
    struct nk_font *font = nk_font_atlas_add_from_file(atlas,
                                                       font_path,
                                                       20.0f,
                                                       &font_cfg);
    nk_glfw3_font_stash_end();

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
    backend->is_dragging = false;
    backend->drag_cursor_start_x = 0.0;
    backend->drag_cursor_start_y = 0.0;
    backend->drag_window_start_x = 0;
    backend->drag_window_start_y = 0;
    backend->drag_cursor_screen_x = 0.0;
    backend->drag_cursor_screen_y = 0.0;
    backend->is_resizing = false;
    backend->resize_cursor_screen_x = 0.0;
    backend->resize_cursor_screen_y = 0.0;
    backend->resize_window_start_width = backend->width;
    backend->resize_window_start_height = backend->height;

    return 0;
}

void render_shutdown(struct render_backend *backend)
{
    if (backend == NULL)
    {
        return;
    }

    nk_glfw3_shutdown();

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
    if (backend == NULL)
    {
        return;
    }

    nk_glfw3_new_frame();
}

void render_end_frame(struct render_backend *backend)
{
    if (backend == NULL)
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

    nk_glfw3_render(NK_ANTI_ALIASING_ON);

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

void render_window_size(const struct render_backend *backend,
                        int *width,
                        int *height)
{
    if (backend == NULL || backend->window == NULL)
    {
        if (width != NULL)
        {
            *width = 0;
        }
        if (height != NULL)
        {
            *height = 0;
        }
        return;
    }

    if (width != NULL)
    {
        *width = backend->width;
    }
    if (height != NULL)
    {
        *height = backend->height;
    }
}

void render_window_request_close(struct render_backend *backend)
{
    if (backend == NULL || backend->window == NULL)
    {
        return;
    }

    glfwSetWindowShouldClose((GLFWwindow *)backend->window, GLFW_TRUE);
}

void render_window_minimize(struct render_backend *backend)
{
    if (backend == NULL || backend->window == NULL)
    {
        return;
    }

    glfwIconifyWindow((GLFWwindow *)backend->window);
}

void render_window_toggle_maximize(struct render_backend *backend)
{
    if (backend == NULL || backend->window == NULL)
    {
        return;
    }

    GLFWwindow *window = (GLFWwindow *)backend->window;
    if (glfwGetWindowAttrib(window, GLFW_MAXIMIZED) == GLFW_TRUE)
    {
        glfwRestoreWindow(window);
    }
    else
    {
        glfwMaximizeWindow(window);
    }
}

bool render_window_is_maximized(const struct render_backend *backend)
{
    if (backend == NULL || backend->window == NULL)
    {
        return false;
    }

    return glfwGetWindowAttrib((GLFWwindow *)backend->window, GLFW_MAXIMIZED) == GLFW_TRUE;
}

void render_window_begin_drag(struct render_backend *backend)
{
    if (backend == NULL || backend->window == NULL)
    {
        return;
    }

    GLFWwindow *window = (GLFWwindow *)backend->window;
    glfwGetCursorPos(window,
                     &backend->drag_cursor_start_x,
                     &backend->drag_cursor_start_y);
    glfwGetWindowPos(window,
                     &backend->drag_window_start_x,
                     &backend->drag_window_start_y);
    backend->drag_cursor_screen_x =
        backend->drag_window_start_x + backend->drag_cursor_start_x;
    backend->drag_cursor_screen_y =
        backend->drag_window_start_y + backend->drag_cursor_start_y;
    backend->is_dragging = true;
}

void render_window_drag_update(struct render_backend *backend)
{
    if (backend == NULL || backend->window == NULL || !backend->is_dragging)
    {
        return;
    }

    GLFWwindow *window = (GLFWwindow *)backend->window;
    double cursor_x = 0.0;
    double cursor_y = 0.0;
    glfwGetCursorPos(window, &cursor_x, &cursor_y);
    int window_x = 0;
    int window_y = 0;
    glfwGetWindowPos(window, &window_x, &window_y);

    double cursor_screen_x = window_x + cursor_x;
    double cursor_screen_y = window_y + cursor_y;

    int target_x = backend->drag_window_start_x + (int)(cursor_screen_x - backend->drag_cursor_screen_x);
    int target_y = backend->drag_window_start_y + (int)(cursor_screen_y - backend->drag_cursor_screen_y);
    glfwSetWindowPos(window, target_x, target_y);
}

void render_window_end_drag(struct render_backend *backend)
{
    if (backend == NULL)
    {
        return;
    }

    backend->is_dragging = false;
}

void render_window_begin_resize(struct render_backend *backend)
{
    if (backend == NULL || backend->window == NULL)
    {
        return;
    }

    if (backend->is_dragging)
    {
        render_window_end_drag(backend);
    }

    GLFWwindow *window = (GLFWwindow *)backend->window;
    double cursor_x = 0.0;
    double cursor_y = 0.0;
    glfwGetCursorPos(window, &cursor_x, &cursor_y);
    int window_x = 0;
    int window_y = 0;
    glfwGetWindowPos(window, &window_x, &window_y);

    backend->resize_cursor_screen_x = window_x + cursor_x;
    backend->resize_cursor_screen_y = window_y + cursor_y;
    backend->resize_window_start_width = backend->width;
    backend->resize_window_start_height = backend->height;
    backend->is_resizing = true;
}

void render_window_resize_update(struct render_backend *backend,
                                 int min_width,
                                 int min_height)
{
    if (backend == NULL || backend->window == NULL || !backend->is_resizing)
    {
        return;
    }

    GLFWwindow *window = (GLFWwindow *)backend->window;
    double cursor_x = 0.0;
    double cursor_y = 0.0;
    glfwGetCursorPos(window, &cursor_x, &cursor_y);
    int window_x = 0;
    int window_y = 0;
    glfwGetWindowPos(window, &window_x, &window_y);

    double cursor_screen_x = window_x + cursor_x;
    double cursor_screen_y = window_y + cursor_y;

    int width_delta = (int)(cursor_screen_x - backend->resize_cursor_screen_x);
    int height_delta = (int)(cursor_screen_y - backend->resize_cursor_screen_y);

    int new_width = backend->resize_window_start_width + width_delta;
    int new_height = backend->resize_window_start_height + height_delta;

    if (new_width < min_width)
    {
        new_width = min_width;
    }
    if (new_height < min_height)
    {
        new_height = min_height;
    }

    glfwSetWindowSize(window, new_width, new_height);
    backend->width = new_width;
    backend->height = new_height;
}

void render_window_end_resize(struct render_backend *backend)
{
    if (backend == NULL)
    {
        return;
    }

    backend->is_resizing = false;
}
