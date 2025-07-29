int sum_of_pow2(int n){
    int sum = 0;
    for(int i = 0; i < n; i++) {
        sum += (1 << i);
    }
    return sum;
}