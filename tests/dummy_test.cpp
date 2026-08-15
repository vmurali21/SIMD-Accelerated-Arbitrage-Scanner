#include <gtest/gtest.h>

extern int dummy_function();

TEST(DummyTest, Returns42) {
    EXPECT_EQ(dummy_function(), 42);
}
