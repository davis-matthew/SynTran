int sum_of_evens(int n){
    int sum = 0;
    for(int i = 1; i <= n; i++) {
        sum += 2 * i;
    }
    return sum;
}