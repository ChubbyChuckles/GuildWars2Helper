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
    app->state.warp_charge = 0.35f;
    app->state.nav_point = 1;
    app->state.flight_mode = 0;
    app->state.signal_noise = 0.12f;
    app->state.anomaly_threshold = 62.0f;
    app->state.drone_deploy = 0.25f;
    app->state.coolant_mix = 0.5f;
    app->state.hud_tint.r = 0.12f;
    app->state.hud_tint.g = 0.85f;
    app->state.hud_tint.b = 0.96f;
    app->state.hud_tint.a = 1.0f;
    app->state.harmonic_channels[0] = 0.35f;
    app->state.harmonic_channels[1] = 0.62f;
    app->state.harmonic_channels[2] = -0.18f;
    app->state.beacon_lock = 0.58f;
    app->state.comm_channel = 7;
    app->state.command_buffer[0] = '\0';
    app->state.drone_online[0] = true;
    app->state.drone_online[1] = false;
    app->state.drone_online[2] = true;
    app->state.stealth_mode = false;
    app->state.spectral_focus = 0.72f;
    app->state.chrono_lag = 3.5f;
    app->state.failsafe_mode = true;
    app->state.cascade_pressure = 0.44f;

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
    struct nk_rect panel_bounds = nk_rect(40.0f, 40.0f, 460.0f, 660.0f);

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

        nk_layout_row_dynamic(ctx, 30.0f, 1);
        nk_label(ctx, "Warp Charge", NK_TEXT_LEFT);
        nk_size warp_charge = (nk_size)(app->state.warp_charge * 100.0f);
        warp_charge = nk_prog(ctx, warp_charge, 100, nk_true);
        app->state.warp_charge = (float)warp_charge / 100.0f;
        if (nk_widget_is_hovered(ctx))
        {
            nk_tooltip(ctx, "Drag to tune the jump capacitors.");
        }

        static const char *nav_points[] = {
            "Arcology Gate",
            "Fractal Lattice",
            "Sage Conflux",
            "Azure Rift",
            "Eon Relay"};
        const int nav_point_count = (int)NK_LEN(nav_points);
        if (app->state.nav_point < 0 || app->state.nav_point >= nav_point_count)
        {
            app->state.nav_point = 0;
        }

        nk_layout_row_dynamic(ctx, 30.0f, 1);
        nk_label(ctx, "Navigation Solution", NK_TEXT_LEFT);
        if (nk_combo_begin_label(ctx,
                                 nav_points[app->state.nav_point],
                                 nk_vec2(280.0f, 200.0f)))
        {
            nk_layout_row_dynamic(ctx, 24.0f, 1);
            for (int i = 0; i < nav_point_count; ++i)
            {
                if (nk_combo_item_label(ctx, nav_points[i], NK_TEXT_LEFT))
                {
                    if (app->state.nav_point != i && app->logger != NULL)
                    {
                        log_message(app->logger,
                                    LOG_LEVEL_INFO,
                                    "Navigation solution locked on %s.",
                                    nav_points[i]);
                    }
                    app->state.nav_point = i;
                }
            }
            nk_combo_end(ctx);
        }

        nk_layout_row_dynamic(ctx, 26.0f, 3);
        static const char *flight_modes[] = {
            "Cruise",
            "Intercept",
            "Evasion"};
        for (int i = 0; i < 3; ++i)
        {
            nk_bool active_mode = app->state.flight_mode == i ? nk_true : nk_false;
            if (nk_option_label(ctx, flight_modes[i], active_mode))
            {
                if (app->state.flight_mode != i && app->logger != NULL)
                {
                    log_message(app->logger,
                                LOG_LEVEL_DEBUG,
                                "Flight profile switched to %s mode.",
                                flight_modes[i]);
                }
                app->state.flight_mode = i;
            }
        }

        nk_layout_row_dynamic(ctx, 24.0f, 1);
        nk_bool stealth = app->state.stealth_mode ? nk_true : nk_false;
        if (nk_checkbox_label(ctx, "Stealth Envelope", &stealth))
        {
            if (app->state.stealth_mode != (stealth == nk_true) &&
                app->logger != NULL)
            {
                log_message(app->logger,
                            LOG_LEVEL_INFO,
                            "Stealth envelope %s",
                            stealth == nk_true ? "engaged" : "released");
            }
            app->state.stealth_mode = (stealth == nk_true);
        }

        nk_layout_row_dynamic(ctx, 30.0f, 1);
        nk_label(ctx, "Signal Noise Threshold", NK_TEXT_LEFT);
        nk_layout_row_dynamic(ctx, 24.0f, 1);
        nk_slider_float(ctx,
                        0.0f,
                        &app->state.signal_noise,
                        1.0f,
                        0.005f);

        nk_layout_row_dynamic(ctx, 30.0f, 1);
        nk_label(ctx, "Anomaly Gate", NK_TEXT_LEFT);
        nk_layout_row_dynamic(ctx, 24.0f, 1);
        nk_property_float(ctx,
                          "Threshold",
                          0.0f,
                          &app->state.anomaly_threshold,
                          120.0f,
                          0.5f,
                          0.2f);

        nk_layout_row_dynamic(ctx, 30.0f, 1);
        nk_label(ctx, "Coolant Mix", NK_TEXT_LEFT);
        nk_layout_row_dynamic(ctx, 24.0f, 1);
        nk_slider_float(ctx,
                        0.0f,
                        &app->state.coolant_mix,
                        1.0f,
                        0.01f);

        nk_layout_row_dynamic(ctx, 28.0f, 1);
        nk_label(ctx, "Drone Deployment", NK_TEXT_LEFT);
        nk_size deployment = (nk_size)(app->state.drone_deploy * 100.0f);
        deployment = nk_prog(ctx, deployment, 100, nk_true);
        app->state.drone_deploy = (float)deployment / 100.0f;

        static const char *drone_names[] = {
            "Scout",
            "Relay",
            "Defense"};
        nk_layout_row_dynamic(ctx, 24.0f, 3);
        for (int i = 0; i < 3; ++i)
        {
            nk_bool online = app->state.drone_online[i] ? nk_true : nk_false;
            nk_selectable_label(ctx,
                                drone_names[i],
                                NK_TEXT_CENTERED,
                                &online);
            app->state.drone_online[i] = (online == nk_true);
        }

        if (nk_tree_push(ctx, NK_TREE_TAB, "Calibration Matrix", NK_MINIMIZED))
        {
            const char *axes[] = {"Alpha", "Beta", "Gamma"};
            nk_layout_row_dynamic(ctx, 24.0f, 2);
            for (int i = 0; i < 3; ++i)
            {
                nk_label(ctx, axes[i], NK_TEXT_LEFT);
                nk_property_float(ctx,
                                  "",
                                  -2.0f,
                                  &app->state.harmonic_channels[i],
                                  2.0f,
                                  0.01f,
                                  0.005f);
            }
            nk_tree_pop(ctx);
        }

        nk_layout_row_dynamic(ctx, 26.0f, 1);
        nk_label(ctx, "HUD Spectral Tint", NK_TEXT_LEFT);
        nk_layout_row_dynamic(ctx, 150.0f, 1);
        app->state.hud_tint = nk_color_picker(ctx, app->state.hud_tint, NK_RGBA);

        nk_layout_row_dynamic(ctx, 24.0f, 1);
        nk_slider_float(ctx,
                        0.0f,
                        &app->state.hud_tint.a,
                        1.0f,
                        0.01f);

        struct nk_color tint_color = nk_rgba_f(app->state.hud_tint.r,
                                               app->state.hud_tint.g,
                                               app->state.hud_tint.b,
                                               app->state.hud_tint.a);
        nk_style_push_color(ctx, &ctx->style.text.color, tint_color);
        nk_layout_row_dynamic(ctx, 22.0f, 1);
        nk_label(ctx, "Spectral uplink synchronized", NK_TEXT_LEFT);
        nk_style_pop_color(ctx);

        nk_layout_row_dynamic(ctx, 30.0f, 1);
        nk_label(ctx, "Command Uplink", NK_TEXT_LEFT);
        nk_layout_row_dynamic(ctx, 28.0f, 1);
        nk_flags edit_flags = nk_edit_string_zero_terminated(ctx,
                                                             NK_EDIT_FIELD,
                                                             app->state.command_buffer,
                                                             sizeof(app->state.command_buffer),
                                                             nk_filter_default);
        if ((edit_flags & NK_EDIT_COMMITED) != 0 && app->logger != NULL)
        {
            if (app->state.command_buffer[0] != '\0')
            {
                log_message(app->logger,
                            LOG_LEVEL_INFO,
                            "Command uplink received: %s",
                            app->state.command_buffer);
                app->state.command_buffer[0] = '\0';
            }
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
                nk_false);

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
        nk_prog(ctx, (nk_size)(drive_wave * 100.0f), 100, nk_false);

        nk_layout_row_dynamic(ctx, 22.0f, 1);
        nk_label(ctx, "Beacon Lock", NK_TEXT_LEFT);
        nk_layout_row_dynamic(ctx, 18.0f, 1);
        nk_prog(ctx,
                (nk_size)(app->state.beacon_lock * 100.0f),
                100,
                nk_false);

        nk_layout_row_dynamic(ctx, 22.0f, 1);
        nk_property_int(ctx,
                        "Comm Channel",
                        1,
                        &app->state.comm_channel,
                        24,
                        1,
                        0.2f);

        nk_layout_row_dynamic(ctx, 24.0f, 1);
        nk_value_float(ctx,
                       "Signal Noise",
                       app->state.signal_noise);

        nk_layout_row_dynamic(ctx, 26.0f, 2);
        if (nk_button_symbol(ctx, NK_SYMBOL_TRIANGLE_RIGHT))
        {
            app->state.beacon_lock += 0.05f;
            if (app->state.beacon_lock > 1.0f)
            {
                app->state.beacon_lock = 1.0f;
            }
            if (app->logger != NULL)
            {
                log_message(app->logger,
                            LOG_LEVEL_DEBUG,
                            "Beacon lock nudged forward.");
            }
        }
        if (nk_button_symbol(ctx, NK_SYMBOL_MINUS))
        {
            app->state.beacon_lock -= 0.05f;
            if (app->state.beacon_lock < 0.0f)
            {
                app->state.beacon_lock = 0.0f;
            }
        }

        struct nk_color diag_tint = nk_rgba_f(app->state.hud_tint.r,
                                              app->state.hud_tint.g,
                                              app->state.hud_tint.b,
                                              app->state.hud_tint.a);
        nk_style_push_color(ctx, &ctx->style.text.color, diag_tint);
        nk_layout_row_dynamic(ctx, 22.0f, 1);
        nk_labelf(ctx,
                  NK_TEXT_LEFT,
                  "Channel %02d link harmonized",
                  app->state.comm_channel);
        nk_style_pop_color(ctx);
    }
    nk_end(ctx);

    if (nk_begin(ctx,
                 "Quantum Diagnostics",
                 nk_rect(500.0f, 320.0f, 320.0f, 320.0f),
                 NK_WINDOW_BORDER | NK_WINDOW_MOVABLE | NK_WINDOW_SCALABLE |
                     NK_WINDOW_TITLE))
    {
        if (nk_group_begin(ctx, "Spectral Sweep", NK_WINDOW_BORDER))
        {
            nk_layout_row_dynamic(ctx, 24.0f, 1);
            nk_slider_float(ctx,
                            0.0f,
                            &app->state.spectral_focus,
                            1.0f,
                            0.0025f);

            nk_layout_row_dynamic(ctx, 24.0f, 1);
            nk_property_float(ctx,
                              "Chrono Lag",
                              0.0f,
                              &app->state.chrono_lag,
                              12.0f,
                              0.1f,
                              0.05f);

            nk_layout_row_dynamic(ctx, 20.0f, 1);
            nk_value_float(ctx,
                           "Spectral",
                           app->state.spectral_focus * 100.0f);

            nk_layout_row_dynamic(ctx, 24.0f, 1);
            nk_size cascade = (nk_size)(app->state.cascade_pressure * 100.0f);
            cascade = nk_prog(ctx, cascade, 100, nk_true);
            app->state.cascade_pressure = (float)cascade / 100.0f;

            nk_layout_row_dynamic(ctx, 26.0f, 2);
            if (nk_button_label(ctx, "Pulse Sync"))
            {
                app->state.spectral_focus = fmodf(app->state.spectral_focus + 0.23f, 1.0f);
                if (app->logger != NULL)
                {
                    log_message(app->logger,
                                LOG_LEVEL_DEBUG,
                                "Quantum pulse synchronized.");
                }
            }
            if (nk_button_label(ctx, "Zero Lag"))
            {
                app->state.chrono_lag = 0.0f;
            }
            if (nk_widget_is_hovered(ctx))
            {
                nk_tooltip(ctx, "Maintains resonance under heavy drift.");
            }

            nk_group_end(ctx);
        }

        nk_layout_row_dynamic(ctx, 24.0f, 1);
        nk_bool failsafe = app->state.failsafe_mode ? nk_true : nk_false;
        if (nk_checkbox_label(ctx, "Failsafe Containment", &failsafe))
        {
            app->state.failsafe_mode = (failsafe == nk_true);
        }

        nk_layout_row_dynamic(ctx, 24.0f, 1);
        nk_labelf(ctx,
                  NK_TEXT_LEFT,
                  "Cascade %.1f%%",
                  app->state.cascade_pressure * 100.0f);

        nk_layout_row_dynamic(ctx, 22.0f, 1);
        nk_labelf(ctx,
                  NK_TEXT_LEFT,
                  "Chrono lag %.2fms",
                  app->state.chrono_lag);

        nk_layout_row_dynamic(ctx, 22.0f, 1);
        nk_labelf(ctx,
                  NK_TEXT_LEFT,
                  "Failsafe %s",
                  app->state.failsafe_mode ? "LOCKED" : "DORMANT");
    }
    nk_end(ctx);
}
