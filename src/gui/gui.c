#include "gui.h"

#include <math.h>
#include <stddef.h>
#include <string.h>

#include "nk_config.h"
#include "../utils/utils.h"

static void push_button_theme(struct nk_context *ctx,
                              struct nk_color normal,
                              struct nk_color hover,
                              struct nk_color active)
{
    nk_style_push_style_item(ctx,
                             &ctx->style.button.normal,
                             nk_style_item_color(normal));
    nk_style_push_style_item(ctx,
                             &ctx->style.button.hover,
                             nk_style_item_color(hover));
    nk_style_push_style_item(ctx,
                             &ctx->style.button.active,
                             nk_style_item_color(active));
    nk_style_push_color(ctx,
                        &ctx->style.button.border_color,
                        nk_rgba(128, 224, 255, 255));
}

static void pop_button_theme(struct nk_context *ctx)
{
    nk_style_pop_color(ctx);
    nk_style_pop_style_item(ctx);
    nk_style_pop_style_item(ctx);
    nk_style_pop_style_item(ctx);
}

int gui_init(struct gui_app *app, const struct gui_config *config)
{
    if (app == NULL || config == NULL)
    {
        return -1;
    }

    memset(app, 0, sizeof(*app));
    app->logger = config->logger;
    app->state.propulsion_level = 0.7f;
    app->state.shield_level = 0.45f;
    app->state.system_temperature = 42.0f;
    app->state.auto_mode = true;
    app->state.pulse_phase = 0.0f;

    return 0;
}

void gui_shutdown(struct gui_app *app)
{
    (void)app;
}

void gui_render(struct gui_app *app,
                struct nk_context *ctx,
                float delta_seconds)
{
    if (app == NULL || ctx == NULL)
    {
        return;
    }

    app->state.pulse_phase += delta_seconds * 2.5f;
    if (app->state.pulse_phase > 2.0f * (float)NK_PI)
    {
        app->state.pulse_phase -= 2.0f * (float)NK_PI;
    }

    float glow = 0.55f + 0.45f * sinf(app->state.pulse_phase);
    struct nk_rect panel_bounds = nk_rect(40.0f, 40.0f, 420.0f, 540.0f);

    if (nk_begin(ctx,
                 "Futuristic Control",
                 panel_bounds,
                 NK_WINDOW_BORDER | NK_WINDOW_MOVABLE | NK_WINDOW_SCALABLE |
                     NK_WINDOW_MINIMIZABLE | NK_WINDOW_TITLE))
    {
        nk_layout_row_dynamic(ctx, 36.0f, 1);
        nk_label(ctx, "Propulsion", NK_TEXT_LEFT);
        nk_layout_row_dynamic(ctx, 26.0f, 1);
        nk_slider_float(ctx,
                        0.0f,
                        &app->state.propulsion_level,
                        1.0f,
                        0.01f);

        nk_layout_row_dynamic(ctx, 36.0f, 1);
        nk_label(ctx, "Shields", NK_TEXT_LEFT);
        nk_layout_row_dynamic(ctx, 26.0f, 1);
        nk_slider_float(ctx,
                        0.0f,
                        &app->state.shield_level,
                        1.0f,
                        0.01f);

        nk_layout_row_dynamic(ctx, 36.0f, 1);
        nk_label(ctx, "Core Temperature (\u00b0C)", NK_TEXT_LEFT);
        nk_layout_row_dynamic(ctx, 30.0f, 1);
        nk_property_float(ctx,
                          "",
                          0.0f,
                          &app->state.system_temperature,
                          120.0f,
                          0.5f,
                          0.2f);

        nk_layout_row_dynamic(ctx, 30.0f, 2);
        bool previous_auto = app->state.auto_mode;
        nk_bool auto_mode = app->state.auto_mode ? nk_true : nk_false;
        nk_checkbox_label(ctx, "Auto Stabilize", &auto_mode);
        app->state.auto_mode = (auto_mode == nk_true);
        if (previous_auto != app->state.auto_mode && app->logger != NULL)
        {
            log_message(app->logger,
                        LOG_LEVEL_INFO,
                        "Auto stabilize %s",
                        app->state.auto_mode ? "enabled" : "disabled");
        }

        struct nk_color normal = nk_rgba_f(0.2f,
                                           0.4f * glow,
                                           0.6f + 0.2f * glow,
                                           1.0f);
        struct nk_color hover = nk_rgba_f(0.3f,
                                          0.5f * glow,
                                          0.8f,
                                          1.0f);
        struct nk_color active = nk_rgba_f(0.4f,
                                           0.8f,
                                           1.0f,
                                           1.0f);

        push_button_theme(ctx, normal, hover, active);
        nk_layout_row_dynamic(ctx, 44.0f, 2);
        if (nk_button_label(ctx, "ENGAGE BOOST"))
        {
            log_message(app->logger,
                        LOG_LEVEL_INFO,
                        "BOOST engaged at %.0f%% thrust.",
                        app->state.propulsion_level * 100.0f);
        }
        if (nk_button_label(ctx, "STABILIZE"))
        {
            log_message(app->logger,
                        LOG_LEVEL_DEBUG,
                        "Stabilizer pulse emitted (shields %.0f%%).",
                        app->state.shield_level * 100.0f);
        }
        pop_button_theme(ctx);

        nk_layout_row_dynamic(ctx, 30.0f, 1);
        nk_prog(ctx,
                (nk_size)(app->state.propulsion_level * 100.0f),
                100,
                NK_FALSE);

        nk_layout_row_dynamic(ctx, 18.0f, 1);
        nk_label(ctx,
                 "Telemetry updates every 250ms",
                 NK_TEXT_LEFT);
    }
    nk_end(ctx);

    if (nk_begin(ctx,
                 "Systems Overview",
                 nk_rect(500.0f, 40.0f, 280.0f, 240.0f),
                 NK_WINDOW_BORDER | NK_WINDOW_MOVABLE | NK_WINDOW_TITLE))
    {
        nk_layout_row_dynamic(ctx, 22.0f, 1);
        nk_label(ctx, "Drive Output", NK_TEXT_LEFT);

        float drive_wave = 0.5f + 0.5f * sinf(app->state.pulse_phase * 1.5f);
        nk_layout_row_dynamic(ctx, 80.0f, 1);
        if (nk_chart_begin(ctx, NK_CHART_LINES, 32, 0.0f, 1.0f))
        {
            for (int i = 0; i < 32; ++i)
            {
                float sample = 0.5f +
                               0.5f * sinf(app->state.pulse_phase +
                                           (float)i * 0.3f);
                nk_chart_push(ctx, sample);
            }
            nk_chart_end(ctx);
        }

        nk_layout_row_dynamic(ctx, 22.0f, 1);
        nk_label(ctx, "Reactor Flux", NK_TEXT_LEFT);
        nk_layout_row_dynamic(ctx, 20.0f, 1);
        nk_prog(ctx, (nk_size)(drive_wave * 100.0f), 100, NK_FALSE);
    }
    nk_end(ctx);
}
