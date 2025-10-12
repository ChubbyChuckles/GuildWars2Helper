#include <stdio.h>
#include <stdlib.h>

#include "gui/gui.h"
#include "render/render.h"
#include "utils/utils.h"

int main(void)
{
    struct log_context logger;
    if (log_context_init(&logger, stdout, LOG_LEVEL_DEBUG) != 0)
    {
        return EXIT_FAILURE;
    }

    struct render_backend renderer;
    const struct render_backend_config render_cfg = {
        .title = "GuildWars2 Helper",
        .width = 1280,
        .height = 720,
        .logger = &logger};

    if (render_init(&renderer, &render_cfg) != 0)
    {
        log_message(&logger, LOG_LEVEL_ERROR, "Renderer initialization failed.");
        return EXIT_FAILURE;
    }

    struct gui_app gui;
    const struct gui_config gui_cfg = {
        .logger = &logger,
        .renderer = &renderer};

    if (gui_init(&gui, &gui_cfg) != 0)
    {
        log_message(&logger, LOG_LEVEL_ERROR, "GUI initialization failed.");
        render_shutdown(&renderer);
        return EXIT_FAILURE;
    }

    struct nk_context *nk = render_context(&renderer);
    if (nk == NULL)
    {
        log_message(&logger, LOG_LEVEL_ERROR, "Nuklear context unavailable.");
        gui_shutdown(&gui);
        render_shutdown(&renderer);
        return EXIT_FAILURE;
    }

    float last_time = render_time_seconds();
    while (!render_should_close(&renderer))
    {
        render_poll_events(&renderer);
        float current_time = render_time_seconds();
        float delta = current_time - last_time;
        if (delta < 0.0f)
        {
            delta = 0.0f;
        }
        last_time = current_time;

        render_begin_frame(&renderer);
        gui_render(&gui, nk, delta);
        render_end_frame(&renderer);
    }

    gui_shutdown(&gui);
    render_shutdown(&renderer);

    return EXIT_SUCCESS;
}
