library(rjson)

data = read.csv("dexy--sim-output.csv", sep=",")

strategy.counts <- table(list(strategy=data$strategy, step=data$step))

png(file="dexy--strategy-counts.png")
barplot(
    strategy.counts, 
    legend.text = TRUE, 
    border=NA, 
    args.legend = pairlist(bty='n')
)
dev.off()

last.period = subset(data, data$step==max(data$step))

png(file="dexy--hist.png")
hist(last.period$points, main="", ylab="Number of Agents", xlab="Final Score")
dev.off()

json.filename = "dexy--sim-results.json"
sim.results <- list( max_points_in_last_period = max(last.period$points))

# Show the contents...
sim.results

write(toJSON(sim.results), json.filename)
