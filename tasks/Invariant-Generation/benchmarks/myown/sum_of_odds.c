int sum_of_odds(int n){
    int sum = 0;
    for(int i = 1; i <= n; i++) {
        sum += (2 * i) - 1;
    }
    return sum;
}