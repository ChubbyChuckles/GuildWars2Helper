#include "test_framework.h"

#include <stdio.h>
#include <string.h>

#include "../src/utils/utils.h"

static void test_log_init_arguments(struct test_context *ctx)
{
    TEST_ASSERT(ctx, log_context_init(NULL, stdout, LOG_LEVEL_INFO) != 0);
    TEST_ASSERT(ctx, log_context_init(&(struct log_context){0}, NULL, LOG_LEVEL_INFO) != 0);
}

static void test_log_filters_levels(struct test_context *ctx)
{
    FILE *capture = tmpfile();
    TEST_ASSERT(ctx, capture != NULL);

    struct log_context logger;
    TEST_ASSERT(ctx, log_context_init(&logger, capture, LOG_LEVEL_INFO) == 0);

    log_message(&logger, LOG_LEVEL_DEBUG, "debug message should be muted");
    log_message(&logger, LOG_LEVEL_ERROR, "critical failure code %d", 42);

    fflush(capture);
    rewind(capture);

    char buffer[512];
    size_t read = fread(buffer, 1, sizeof(buffer) - 1, capture);
    buffer[read] = '\0';

    TEST_ASSERT(ctx, strstr(buffer, "critical failure code 42") != NULL);
    TEST_ASSERT(ctx, strstr(buffer, "debug message") == NULL);

    fclose(capture);
}

static const struct test_case TESTS[] = {
    {"log_init_arguments", test_log_init_arguments},
    {"log_filters_levels", test_log_filters_levels}};

int main(void)
{
    test_run_all(TESTS, sizeof(TESTS) / sizeof(TESTS[0]));
    return 0;
}
