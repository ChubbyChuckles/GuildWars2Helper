#include "utils.h"

#include <stdarg.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

static void write_timestamp(FILE *stream)
{
    time_t now = time(NULL);
    struct tm tm_now;

#if defined(_WIN32)
    localtime_s(&tm_now, &now);
#else
    localtime_r(&now, &tm_now);
#endif

    char buffer[32];
    if (strftime(buffer, sizeof(buffer), "%Y-%m-%d %H:%M:%S", &tm_now) == 0)
    {
        buffer[0] = '\0';
    }

    if (buffer[0] != '\0')
    {
        fprintf(stream, "[%s] ", buffer);
    }
}

int log_context_init(struct log_context *ctx,
                     FILE *stream,
                     enum log_level min_level)
{
    if (ctx == NULL || stream == NULL)
    {
        return -1;
    }

    ctx->stream = stream;
    ctx->min_level = min_level;
    return 0;
}

void log_context_set_level(struct log_context *ctx, enum log_level level)
{
    if (ctx != NULL)
    {
        ctx->min_level = level;
    }
}

const char *log_level_label(enum log_level level)
{
    switch (level)
    {
    case LOG_LEVEL_TRACE:
        return "TRACE";
    case LOG_LEVEL_DEBUG:
        return "DEBUG";
    case LOG_LEVEL_INFO:
        return "INFO";
    case LOG_LEVEL_WARN:
        return "WARN";
    case LOG_LEVEL_ERROR:
        return "ERROR";
    default:
        return "UNKNOWN";
    }
}

void log_message(struct log_context *ctx,
                 enum log_level level,
                 const char *format,
                 ...)
{
    if (ctx == NULL || ctx->stream == NULL || format == NULL)
    {
        return;
    }

    if (level < ctx->min_level)
    {
        return;
    }

    write_timestamp(ctx->stream);
    fprintf(ctx->stream, "[%s] ", log_level_label(level));

    va_list args;
    va_start(args, format);
    vfprintf(ctx->stream, format, args);
    va_end(args);

    fputc('\n', ctx->stream);
    fflush(ctx->stream);
}
