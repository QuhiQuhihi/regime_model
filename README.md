# Quantitative strategy with python
## Detecting Regime of markets
Backtesting quantitative idea has significant drawbacks. If we test idea in single regime such as late 2020 to early 2022, the idea won't work in other regime such as late 2022.

However, it is really difficult to get label data from financial market. Eventhough S&P500 index reached below 4000, it is really difficult to say that it is recession. Of course some might argue that it is recession, but other might say that it is not recession.

In addition, labelling market data daily or hourly is demading job. Single mistake might lead to huge loss at investment. Group of finance experts might be able to label market data. But this idea is unrealistic.

So, detecting regime shift or labelling regime automatically with algorithm will add great value to finance industry.

## Gausian Mixture Model
Use Gausian mixture model and Hidden Markov model to catch regime shift of the market. Multiple asset classes such as stock, bond, real estate and commodity are used to detect regime shift.   
Original idea from Alex Botte and Doris Bao from Two Sigma. Original article can be found in below link.   
    
[Article] https://www.twosigma.com/articles/a-machine-learning-approach-to-regime-modeling/  
[Blog] https://quhiquhihi.github.io/posts/Regime_Model(Markov-Model)/  

## Greedy Gausian Segmentation
Use Greedy Gausian Segmentation model to catch regime shift of market. Single asset class (US Equity) is used to detect regime shift.  
Original idea from David Hallac, Peter Nystrup, Stephen Boyd of Stanford University.   
    
[Paper] https://web.stanford.edu/~boyd/papers/pdf/ggs.pdf  
[Blog] https://quhiquhihi.github.io/posts/Regime_Model(Gausian-Segmentation)/  
