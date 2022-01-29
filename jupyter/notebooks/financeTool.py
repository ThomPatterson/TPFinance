import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker

expenses_by_year = pd.DataFrame()
income_by_year = pd.DataFrame()
nonretirement_investments_by_year = pd.DataFrame()
retirement_investments_by_year = pd.DataFrame()

nonretirement_account_settings = {}
retirement_account_settings = {}

networth_by_year = pd.DataFrame()
current_year = 0
current_age = 0
death_age = 0

#For Monte Carlo analysis, how many iterations will be run?
num_samples = 10000

#at what age are retirement investments available?
retirement_age = 60

def setup(cy, ca, da):
    global current_year
    global current_age
    global death_age
    current_year = cy
    current_age = ca
    death_age = da
    
    expenses_by_year.insert(0, 'age', range(current_age, death_age))
    expenses_by_year.insert(1, 'year', range(current_year, current_year + (death_age - current_age)))
    income_by_year.insert(0, 'age', range(current_age, death_age))
    income_by_year.insert(1, 'year', range(current_year, current_year + (death_age - current_age)))
    nonretirement_investments_by_year.insert(0, 'age', range(current_age, death_age))
    nonretirement_investments_by_year.insert(1, 'year', range(current_year, current_year + (death_age - current_age)))
    retirement_investments_by_year.insert(0, 'age', range(current_age, death_age))
    retirement_investments_by_year.insert(1, 'year', range(current_year, current_year + (death_age - current_age)))
    networth_by_year.insert(0, 'age', range(current_age, death_age))
    networth_by_year.insert(1, 'year', range(current_year, current_year + (death_age - current_age)))
    



def generate_series(low, high):
    STD_DEV_90 = 3.29#converting from a 90% Confidence Interval to a Standard Deviation
    mean = (low + high) /2
    stddev = (high - low) / STD_DEV_90
    series = pd.Series(np.random.normal(mean, stddev, num_samples))
    return series    


def generate_series_for_year(amt_low, 
                            amt_high, 
                            growth_perc_low, 
                            growth_perc_high,
                            contrib_amt_low,
                            contrib_amt_high
                            ):
    #generate series
    amt_series = generate_series(amt_low, amt_high)
    growth_percent_series = generate_series(growth_perc_low, growth_perc_high)
    contrib_series = generate_series(contrib_amt_low, contrib_amt_high)
    
    #generate series with contrib amt added to balance amt
    x = amt_series.add(contrib_series)
    
    #calculate growth
    y = x.multiply(growth_percent_series)
    
    #add it all up
    total_series = x.add(y)
    
    return total_series


def add_item(df,
             isInvestment=False,
             name=None, 
             starting_amt_low=None, 
             starting_amt_high=None, 
             start_age=None, 
             end_age=None, 
             growth_perc_low=0, 
             growth_perc_high=0, 
             annual_contrib_amt_low=0,
             annual_contrib_amt_high=0,
             annual_contrib_start_age=0,
             annual_contrib_end_age=0
            ):
    
    #input sanitization
    if name is None:
        raise Exception("name is required for all items")
        
    if starting_amt_low is None:
        raise Exception(name, "starting_amt_low is required for all items.  Note this can be the same value as starting_amt_high.")
        
    if starting_amt_high is None:
        raise Exception(name, "starting_amt_high is required for all items.  Note this can be the same value as starting_amt_low.")
        
    if starting_amt_low > starting_amt_high:
        raise Exception(name, "starting_amt_low cannot be greater than starting_amt_high")
        
    if start_age is None:
        raise Exception(name, "start_age is required for all items.")
    
    if (end_age is None) or (end_age == start_age):
        end_age = start_age + 1
        
    if end_age < start_age:
        raise Exception(name, "end_age cannot be less than start_age")
        
    if growth_perc_low > growth_perc_high:
        raise Exception(name, "growth_perc_low cannot be greater than growth_perc_high.  Note they can have the same value.")
        
    if annual_contrib_amt_low > annual_contrib_amt_high:
        raise Exception(name, "annual_contrib_amt_low cannot be greater than annual_contrib_amt_high.  Note they can have the same value.")
        
    if annual_contrib_start_age > annual_contrib_end_age:
        raise Exception(name, "annual_contrib_start_age cannot be greater than annual_contrib_end_age.")
        
    if isInvestment == False:
        if annual_contrib_amt_low > 0: 
            raise Exception(name, "annual_contrib_amt_low only applies to investments.")
        if annual_contrib_amt_high > 0: 
            raise Exception(name, "annual_contrib_amt_high only applies to investments.")
        if annual_contrib_start_age > 0: 
            raise Exception(name, "annual_contrib_start_age only applies to investments.")
        if annual_contrib_end_age > 0: 
            raise Exception(name, "annual_contrib_end_age only applies to investments.")
    
    #add a column for the low and high values to the df
    balance_low_name = name + " balance low" if isInvestment else name + " low"
    balance_high_name = name + " balance high" if isInvestment else name + " high"
    df.insert(len(df.columns), balance_low_name, 0.0)
    df.insert(len(df.columns), balance_high_name, 0.0)
    
    #if this is an investment, add columns for distribution low and high amounts
    if isInvestment:
        distribution_low_name = name + " distribution low"
        distribution_high_name = name + " distribution high"
        df.insert(len(df.columns), distribution_low_name, 0.0)
        df.insert(len(df.columns), distribution_high_name, 0.0)
    
    set_item_balances(df, 
                      start_age, 
                      end_age,
                      growth_perc_low, 
                      growth_perc_high, 
                      starting_amt_low,
                      balance_low_name,
                      starting_amt_high,
                      balance_high_name,
                      annual_contrib_amt_low, 
                      annual_contrib_amt_high, 
                      annual_contrib_start_age, 
                      annual_contrib_end_age
                     )


def set_item_balances(df, 
                      start_age, 
                      end_age,
                      growth_perc_low, 
                      growth_perc_high, 
                      starting_amt_low,
                      amt_low_name,
                      starting_amt_high,
                      amt_high_name,
                      annual_contrib_amt_low, 
                      annual_contrib_amt_high, 
                      annual_contrib_start_age, 
                      annual_contrib_end_age
                     ):
    #get the rows for the affected years
    years_affected = df.loc[(df['age'] >= start_age) & (df['age'] < end_age)]
    
    amt_low = starting_amt_low
    amt_high = starting_amt_high

    for i, row in years_affected.iterrows():
        age = row['age']
        contrib_year = (age >= annual_contrib_start_age) and (age < annual_contrib_end_age)
        contrib_low = annual_contrib_amt_low if contrib_year else 0
        contrib_high = annual_contrib_amt_high if contrib_year else 0
        
        year_expenses = generate_series_for_year(
            amt_low, 
            amt_high, 
            growth_perc_low, 
            growth_perc_high,
            contrib_low,
            contrib_high,
        )

        #get 90% bounds and set amt_low and amt_high for next iteration
        amt_low = year_expenses.quantile(0.05)
        amt_high = year_expenses.quantile(0.95)
        
        #note, i is accurate since years_affected is just a view of df
        df.loc[i, amt_low_name] = amt_low
        df.loc[i, amt_high_name] = amt_high

        
def add_expense(**kwargs):
    
    add_item(expenses_by_year, isInvestment=False, **kwargs)
    
def add_income(**kwargs):
    add_item(income_by_year, isInvestment=False, **kwargs)
    
def add_nonretirement_investment(end_age=None,
                                 growth_perc_low=0, 
                                 growth_perc_high=0, 
                                 annual_contrib_amt_low=0,
                                 annual_contrib_amt_high=0,
                                 annual_contrib_start_age=0,
                                 annual_contrib_end_age=0,
                                 **kwargs
                                ):
    #since I'm using kwargs to persist account settings I need to make sure it has all the optional values
    start_age = kwargs['start_age']
    if (end_age is None) or (end_age==start_age):
        end_age = start_age + 1
    kwargs['end_age'] = end_age
    kwargs['growth_perc_low'] = growth_perc_low
    kwargs['growth_perc_high'] = growth_perc_high
    kwargs['annual_contrib_amt_low'] = annual_contrib_amt_low
    kwargs['annual_contrib_amt_high'] = annual_contrib_amt_high
    kwargs['annual_contrib_start_age'] = annual_contrib_start_age
    kwargs['annual_contrib_end_age'] = annual_contrib_end_age
        
        
    add_item(nonretirement_investments_by_year, isInvestment=True, **kwargs)
    
    #persist the settings for recalculating account balances after distributions
    nonretirement_account_settings[kwargs['name']] = kwargs
    
def add_retirement_investment(end_age=None,
                              growth_perc_low=0, 
                              growth_perc_high=0, 
                              annual_contrib_amt_low=0,
                              annual_contrib_amt_high=0,
                              annual_contrib_start_age=0,
                              annual_contrib_end_age=0,
                              **kwargs
                             ):
    #since I'm using kwargs to persist account settings I need to make sure it has all the optional values
    start_age = kwargs['start_age']
    if (end_age is None) or (end_age==start_age):
        end_age = start_age + 1
    kwargs['end_age'] = end_age
    kwargs['growth_perc_low'] = growth_perc_low
    kwargs['growth_perc_high'] = growth_perc_high
    kwargs['annual_contrib_amt_low'] = annual_contrib_amt_low
    kwargs['annual_contrib_amt_high'] = annual_contrib_amt_high
    kwargs['annual_contrib_start_age'] = annual_contrib_start_age
    kwargs['annual_contrib_end_age'] = annual_contrib_end_age
    
    add_item(retirement_investments_by_year, isInvestment = True, **kwargs)
    
    #persist the settings for recalculating account balances after distributions
    retirement_account_settings[kwargs['name']] = kwargs
    
def get_item_names(df):
    #discover existing items from referenced dataframe
    item_names = []
    for name in df.columns.values:
        if ("low" in name) and ("distribution" not in name):
            item_names.append(name[0:len(name)-4]) #slice off " low"
    return item_names

def process_expenses():
    
    #nonretirement_item_names = get_item_names(nonretirement_investments_by_year)
    #retirement_item_names = get_item_names(retirement_investments_by_year)
    
    #loop over each year
    for i, row in expenses_by_year.iterrows():
        
        #get expense and income totals
        total_expenses_low = row["total low"]
        total_expenses_high = row["total high"]
        total_income_low = income_by_year.loc[i, "total low"]
        total_income_high = income_by_year.loc[i, "total high"]
        
        #generate series
        total_expenses_series = generate_series(total_expenses_low, total_expenses_high)
        total_income_series = generate_series(total_income_low, total_income_high)
        
        #create a new series of income - expense
        income_shortfall_series = total_income_series.subtract(total_expenses_series)

        if income_shortfall_series.min() < 0:
            
            #replace any positive values with 0, there's no need for a "distribution" for those cases
            # (only negative values represent a shortfall)
            clipped_income_shortfall_series = income_shortfall_series.clip(upper=0)
            
            remaining_shortfall = clipped_income_shortfall_series
            if len(nonretirement_account_settings) > 0:
                remaining_shortfall = take_distribution_from_investment(nonretirement_investments_by_year, 
                                                                        i,
                                                                        nonretirement_account_settings, 
                                                                        clipped_income_shortfall_series)
            
            if remaining_shortfall is not None:
                #there is still income shortfall after non-retirement accounts
                if (row["age"] >= retirement_age) and (len(retirement_account_settings) > 0):
                    remaining_shortfall = take_distribution_from_investment(retirement_investments_by_year, 
                                                                            i,
                                                                            retirement_account_settings, 
                                                                            remaining_shortfall)
                                              
            
            
def take_distribution_from_investment(investment_df,
                                      row_index,
                                      investment_account_settings,
                                      shortfall_series
                                     ):
                                              
    investment_item_names = get_item_names(investment_df)
                                              
    clipped_income_shortfall_series = shortfall_series                                     
    
    still_short = True
    account_index = 0;
    while still_short:

        #what is the name of this account?
        account_name_unclean = investment_item_names[account_index]
        account_name =  account_name_unclean[0:len(account_name_unclean)-8] #clip off " balance"

        #get account balance values
        account_balance_low = investment_df.loc[row_index, account_name + " balance low"]
        account_balance_high = investment_df.loc[row_index, account_name + " balance high"]

        #generate a series of balance values
        account_balance_series = generate_series(account_balance_low, account_balance_high)

        #generate a new series of balance - (clipped) shortfall.  Note "add" because shortfall vals are negative
        remaining_account_balance_series = account_balance_series.add(clipped_income_shortfall_series)

        #determine new low and high
        remaining_low = (remaining_account_balance_series.quantile(0.05) 
                         if remaining_account_balance_series.quantile(0.05) > 0 
                         else 0)
        remaining_high = (remaining_account_balance_series.quantile(0.95) 
                         if remaining_account_balance_series.quantile(0.95) > 0 
                         else 0)

        #set new account balance values
        investment_df.loc[row_index, account_name + " balance low"] = remaining_low
        investment_df.loc[row_index, account_name + " balance high"] = remaining_high

        #set the distribution amount.  Set negative values to 0, record the delta between initial balance and clipped remaining
        positive_remaining_balance_series = remaining_account_balance_series.clip(lower=0)
        distribution_balance_series = account_balance_series.subtract(positive_remaining_balance_series)
        dist_low = distribution_balance_series.quantile(0.05)
        dist_high = distribution_balance_series.quantile(0.95)
        investment_df.loc[row_index, account_name + " distribution low"] = dist_low
        investment_df.loc[row_index, account_name + " distribution high"] = dist_high

        #recalculate all the future balances of this account
        set_item_balances(investment_df, 
              investment_df.loc[row_index, "age"] + 1, 
              investment_account_settings[account_name]['end_age'],
              investment_account_settings[account_name]['growth_perc_low'], 
              investment_account_settings[account_name]['growth_perc_high'], 
              remaining_low,
              account_name + " balance low",
              remaining_high,
              account_name + " balance high",
              investment_account_settings[account_name]['annual_contrib_amt_low'], 
              investment_account_settings[account_name]['annual_contrib_amt_high'], 
              investment_account_settings[account_name]['annual_contrib_start_age'], 
              investment_account_settings[account_name]['annual_contrib_end_age']
             )

        if remaining_account_balance_series.min() < 0:#there are still cases where there is a shortfall
            #replace any positive values with 0, there's no need for a "distribution" for those cases
            clipped_income_shortfall_series = remaining_account_balance_series.clip(upper=0)

            #increment the account index
            account_index += 1

            #check if this index is a valid account
            if account_index >= len(investment_item_names):
                still_short = False
        else:
            #there is no more shortfall
            clipped_income_shortfall_series = None                                  
            still_short = False
                                              
    return clipped_income_shortfall_series
                                      

def generate_total(df):
    
    item_names = get_item_names(df)
    
    #add a column for the low and high values to the df
    df.insert(len(df.columns), "total low", 0.0)
    df.insert(len(df.columns), "total high", 0.0)
    
    #loop over each year
    for i, row in df.iterrows():
        
        total = pd.Series(np.repeat(0, num_samples))
        for name in item_names:
            low = row[name + " low"]
            high = row[name + " high"]
            amt_series = generate_series(low, high)
            new_total = total.add(amt_series)
            total = new_total
        
        amt_low = total.quantile(0.05)
        amt_high = total.quantile(0.95)
        df.loc[i, "total low"] = amt_low
        df.loc[i, "total high"] = amt_high

def generate_networth():
    networth_by_year.insert(len(networth_by_year.columns), 'networth low', 0.0)
    networth_by_year.insert(len(networth_by_year.columns), 'networth high', 0.0)

    for i, row in networth_by_year.iterrows():
        
        #get totals
        income_low = income_by_year.loc[i, "total low"]
        income_high = income_by_year.loc[i, "total high"]
        expenses_low = expenses_by_year.loc[i, "total low"]
        expenses_high = expenses_by_year.loc[i, "total high"]
        nonret_investments_low = nonretirement_investments_by_year.loc[i, "total low"]
        nonret_investments_high = nonretirement_investments_by_year.loc[i, "total high"]
        ret_investments_low = retirement_investments_by_year.loc[i, "total low"]
        ret_investments_high = retirement_investments_by_year.loc[i, "total high"]
        
        #generate series
        income_series = generate_series(income_low, income_high)
        expenses_series = generate_series(expenses_low, expenses_high)
        nonret_investments_series = generate_series(nonret_investments_low, nonret_investments_high)
        ret_investments_series = generate_series(ret_investments_low, ret_investments_high)
        
        networth_without_retirement = income_series.add(nonret_investments_series).subtract(expenses_series)
        networth_with_retirement = networth_without_retirement.add(ret_investments_series)
        
        if row['age'] < retirement_age:
            networth_by_year.loc[i, 'networth low'] = networth_without_retirement.quantile(0.05)
            networth_by_year.loc[i, 'networth high'] = networth_without_retirement.quantile(0.95)
        else:
            networth_by_year.loc[i, 'networth low'] = networth_with_retirement.quantile(0.05)
            networth_by_year.loc[i, 'networth high'] = networth_with_retirement.quantile(0.95)
        
def generate_totals():
    generate_total(income_by_year)
    generate_total(expenses_by_year)
    process_expenses()
    generate_total(nonretirement_investments_by_year)
    generate_total(retirement_investments_by_year)
    generate_networth()
    write_csv_files()
        
def generate_amounts_for_graph(df):
    
    # create new dataframe that just holds the values we want to graph
    all_values = pd.DataFrame({
        "age":  range(current_age, death_age), 
        "low":  np.repeat(0, death_age-current_age), 
        "high": np.repeat(0, death_age-current_age), 
        "mean": np.repeat(0, death_age-current_age)
    })
    
    # all I'm really doing right now is adding mean, 
    # but this gives me room for future expansion if I wanted to include percentiles or something
    for i, row in df.iterrows():
        age = row["age"]
        total_low = row["total low"]
        total_high = row["total high"]
        total_mean = (total_high + total_low) / 2
        
        all_values.loc[i, "low"] = total_low
        all_values.loc[i, "high"] = total_high
        all_values.loc[i, "mean"] = total_mean

    return all_values


def show_account_types_graph(start_age=0, 
                             end_age=0, 
                             yMax=None,
                             lines=[], 
                             showRetirementLine=True,
                             showIncome=True,
                             showExpenses=True,
                             showNonRetirement=True,
                             showRetirement=True
                            ):
        
    #get series massaged for graphing
    expense_data = generate_amounts_for_graph(expenses_by_year)
    income_data = generate_amounts_for_graph(income_by_year)
    nonret_investment_data = generate_amounts_for_graph(nonretirement_investments_by_year)
    ret_investment_data = generate_amounts_for_graph(retirement_investments_by_year)
    
    #create graph
    fig, ax = plt.subplots(figsize=(20,10))
    
    #plot the ranges
    legends = []
    
    if showIncome:
        ax.fill_between(income_data.age, income_data.low, income_data.high, color="green", alpha=0.2)
        legends.append("Income")
    
    if showNonRetirement:
        ax.fill_between(nonret_investment_data.age, nonret_investment_data.low, nonret_investment_data.high, color="blue", alpha=0.2)
        legends.append("Non-Retirement Investments")
    
    if showRetirement:
        ax.fill_between(ret_investment_data.age, ret_investment_data.low, ret_investment_data.high, color="purple", alpha=0.2)
        legends.append("Retirement Investments")
    
    if showExpenses:
        ax.fill_between(expense_data.age, expense_data.low, expense_data.high, color="red", alpha=0.2)
        legends.append("Expenses")
    
    #set bounds
    ax.set_ylim(bottom=0, top=yMax)
    x_left = current_age if start_age == 0 else start_age
    x_right = death_age if end_age == 0 else end_age
    ax.set_xlim(left=x_left, right=x_right)
    
    #format axes
    fmt = '${x:,.0f}'
    tick = ticker.StrMethodFormatter(fmt)
    ax.yaxis.set_major_formatter(tick)
    ax.xaxis.set_minor_locator(ticker.AutoMinorLocator())
    
    #add grid lines
    plt.grid()
    
    #show retirement line
    ymin, ymax = ax.get_ylim()
    text_y = ymax - (ymax * .05)
    if showRetirementLine:
        ax.axvline(x=retirement_age)
        ax.text(x=retirement_age, y=text_y, s="Retirement Investments Available", rotation=270, ha='left', va='top')
        
    #show user lines
    for line in lines:
        ax.axvline(x=line[0])
        ax.text(x=line[0], y=text_y, s=line[1], rotation=270, ha='left', va='top')
    
    #set labels
    plt.xlabel('Age')
    
    #show legend
    ax.legend(legends, loc="upper right")
    
    #save it as a PNG
    plt.savefig('../data/account-types-graph.png')
    
    #show it in jupyter
    plt.show()
    
    
def show_networth_graph(start_age=0, 
                        end_age=0, 
                        yMax=None,
                        yMin=None,
                        lines=[], 
                        showRetirementLine=True,
                        ):

    #create graph
    fig, ax = plt.subplots(figsize=(20,10))
    
    nw_low = networth_by_year['networth low']
    nw_high = networth_by_year['networth high']
    
    #get bounds of graph if not set
    if (yMax is None):
        yMax = nw_high.max()
        
    if (yMin is None):
        yMin = nw_low.min()
    
    #draw everything above zero as green, everything below as red.
    #overlay the network as a solid white, then do it again as a see-through blue
    ax.fill_between(networth_by_year.age, 0, yMax, color="green", alpha=0.1)
    ax.fill_between(networth_by_year.age, 0, yMin, color="red", alpha=0.1)
    ax.fill_between(networth_by_year.age, nw_low, nw_high, color="white", alpha=1)
    legend_handle = ax.fill_between(networth_by_year.age, nw_low, nw_high, color="blue", alpha=0.1, label="Networth")
    
    ax.plot(networth_by_year.age, nw_high, linewidth=2, color="black")
    ax.plot(networth_by_year.age, nw_low, linewidth=2, color="black")

    #set bounds
    ax.set_ylim(bottom=yMin, top=yMax)
    x_left = current_age if start_age == 0 else start_age
    x_right = death_age if end_age == 0 else end_age
    ax.set_xlim(left=x_left, right=x_right)
    
    #format axes
    fmt = '${x:,.0f}'
    tick = ticker.StrMethodFormatter(fmt)
    ax.yaxis.set_major_formatter(tick)
    ax.xaxis.set_minor_locator(ticker.AutoMinorLocator())
    
    #add grid lines
    plt.grid()
    
    #show retirement line
    ymin, ymax = ax.get_ylim()
    text_y = ymax - (ymax * .05)
    if showRetirementLine:
        ax.axvline(x=retirement_age)
        ax.text(x=retirement_age, y=text_y, s="Retirement Investments Available", rotation=270, ha='left', va='top')
        
    #show user lines
    for line in lines:
        ax.axvline(x=line[0])
        ax.text(x=line[0], y=text_y, s=line[1], rotation=270, ha='left', va='top')
    
    #set labels
    plt.xlabel('Age')
    
    #show legend
    ax.legend(handles=[legend_handle])
    
    #save it as a PNG
    plt.savefig('../data/networth-graph.png')
    
    #show it in jupyter
    plt.show()
    
    
def write_csv_files():
    expenses_by_year.to_csv('../data/expenses.csv')
    income_by_year.to_csv('../data/income.csv')
    nonretirement_investments_by_year.to_csv('../data/nonretirement-investments.csv')
    retirement_investments_by_year.to_csv('../data/retirement-investments.csv')
    networth_by_year.to_csv('../data/networth.csv')