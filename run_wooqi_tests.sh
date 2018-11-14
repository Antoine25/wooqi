#!/bin/bash

RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'
export RED
export GREEN
export NC


testing/postfail_feature/./run_wooqi_postfail_tests.sh
result1=$? |bc

testing/reruns_feature/./run_wooqi_reruns_tests.sh
result2=$? |bc

testing/uut_feature/./run_wooqi_uut_tests.sh
result3=$? |bc

testing/uut2_feature/./run_wooqi_uut2_tests.sh
result4=$? |bc

testing/loop_feature/./run_wooqi_loop_tests.sh
result5=$? |bc

testing/cache_feature/./run_wooqi_cache_tests.sh
result6=$? |bc

testing/range_feature/./run_wooqi_range_tests.sh
result7=$? |bc

echo $result7

echo $result1 || $result2 || $result3 || $result4 || $result5 || $result6 || $result7

exit $result1 || $result2 || $result3 || $result4 || $result5 || $result6 || $result7
