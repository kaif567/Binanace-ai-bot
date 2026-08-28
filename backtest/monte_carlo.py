import random
import numpy as np



def monte_carlo_simulation(
        trade_history,
        simulations=1000
):


    # Extract trade returns

    returns = []


    for trade in trade_history:


        if "profit" in trade:

            returns.append(
                trade["profit"]
            )



    if len(returns) == 0:

        return {

            "error":
            "No completed trades"

        }



    results = []



    for _ in range(simulations):


        balance = 1000


        # Randomly shuffle trades

        shuffled = random.choices(
            returns,
            k=len(returns)
        )


        for trade in shuffled:


            balance += trade



        results.append(
            balance
        )



    results=np.array(results)



    profitable = (
        results > 1000
    ).sum()



    probability = (
        profitable /
        simulations
    ) * 100



    return {


        "simulations":
        simulations,


        "starting_balance":
        1000,


        "average":
        round(
            np.mean(results),
            2
        ),


        "best_case":
        round(
            np.max(results),
            2
        ),


        "worst_case":
        round(
            np.min(results),
            2
        ),


        "median":
        round(
            np.median(results),
            2
        ),


        "profit_probability":
        round(
            probability,
            2
        )

    }