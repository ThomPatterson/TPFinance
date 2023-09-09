import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import warnings

#####
# These are the four main DataFrames that are used as the state for everything
#####
expenses_by_year = pd.DataFrame()
income_by_year = pd.DataFrame()
nonretirement_investments_by_year = pd.DataFrame()
retirement_investments_by_year = pd.DataFrame()

#####
# When running the simulation to process expenses it will be necessary to take a distribution from investments
# This will require recalculating the balances of that investment for that year and all subsequent years
# To do this we need to store the values that were used to create the investments initially so we can reference them when its recalculated
#####
nonretirement_account_settings = {}
retirement_account_settings = {}

networth_by_year = pd.DataFrame()
message_log = []
current_year = 0
current_age = 0
death_age = 0

#For Monte Carlo analysis, how many iterations will be run?
num_samples = 10000

#at what age are retirement investments available?
retirement_age = 60

def log(message, year=None, age=None):
    if (year is None) or (age is None):
        message_log.append(message)
    else:
        message_log.append("In " + str(int(year)) + " at age " + str(int(age)) + ": " + message)
        
def write_log():
    with open("../data/log.txt", "w") as output:
        #output.write(str(message_log))
        #output.write("".format("\n".join(message_log[1:])))
        multi_line_output = '\n'.join([i for i in message_log[1:]])
        output.write(multi_line_output)

def write_csv_files():
    expenses_by_year.to_csv('../data/expenses.csv')
    income_by_year.to_csv('../data/income.csv')
    nonretirement_investments_by_year.to_csv('../data/nonretirement-investments.csv')
    retirement_investments_by_year.to_csv('../data/retirement-investments.csv')
    networth_by_year.to_csv('../data/networth.csv')
        
def usd_fmt(num):
    return '${:0,.2f}'.format(num).replace('$-','-$')

# helper function to allow you to check what an income is at some specified age
def get_income_for_age(name, age):
    df = income_by_year
    return {
        'low': int(df.loc[df['age']==age, name + " low"]),
        'high': int(df.loc[df['age']==age, name + " high"])
    }

# helper function to allow you to check what an expense is at some specified age
def get_expense_for_age(name, age):
    df = expenses_by_year
    return {
        'low': int(df.loc[df['age']==age, name + " low"]),
        'high': int(df.loc[df['age']==age, name + " high"])
    }
    
# helper function to allow you to check what a nonretirement account balance is at some specified age
# warning: this will give values before expenses have been processed.  This should not be relied on.
def get_nonretirement_balance_for_age(name, age):
    warnings.warn("It is not safe to trust investment account balances before expenses have been processed (usually by generate_totals())")
    df = nonretirement_investments_by_year
    return {
        'low': int(df.loc[df['age']==age, name + " balance low"]),
        'high': int(df.loc[df['age']==age, name + " balance high"])
    }

# helper function to allow you to check what a retirement account balance is at some specified age
# warning: this will give values before expenses have been processed.  This should not be relied on.
def get_retirement_balance_for_age(name, age):
    warnings.warn("It is not safe to trust investment account balances before expenses have been processed (usually by generate_totals())")
    df = retirement_investments_by_year
    return {
        'low': int(df.loc[df['age']==age, name + " balance low"]),
        'high': int(df.loc[df['age']==age, name + " balance high"])
    }

# Start populating the four dataframes with age and year columns 
# And a row from every year from current_year to death_age
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
    


# Given two values that together represent the bounds of a 90% confidence interval
# Create and return a normal distribution with num_samples items that fit those bounds
def generate_series(low, high):
    STD_DEV_90 = 3.29#converting from a 90% Confidence Interval to a Standard Deviation
    mean = (low + high) /2
    stddev = (high - low) / STD_DEV_90
    series = pd.Series(np.random.normal(mean, stddev, num_samples))
    return series    


# Creates a series with num_samples items that represents 
# ((amount + contribution) + ((amount + contribution) * growth_percent))
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


# Adds a new items to the specified DataFrame
# Does input sanitization and adds the necessary columns to the DataFrame
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
    #####
    # input sanitization
    #####
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
    
    
    #####
    # add a column for the low and high values to the df
    #####
    balance_low_name = name + " balance low" if isInvestment else name + " low"
    balance_high_name = name + " balance high" if isInvestment else name + " high"
    df.insert(len(df.columns), balance_low_name, 0.0)
    df.insert(len(df.columns), balance_high_name, 0.0)
    
    #####
    # if this is an investment, add columns for distribution low and high amounts
    #####
    if isInvestment:
        distribution_low_name = name + " distribution low"
        distribution_high_name = name + " distribution high"
        df.insert(len(df.columns), distribution_low_name, 0.0)
        df.insert(len(df.columns), distribution_high_name, 0.0)
    
    #####
    # Now that we have the appropriate columns, set the balances for rows in that column
    #####
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


# Sets the balance in rows for specified columns (amt_low_name & amt_high_name) between specified start and end age
# Will blow away any previous values.  
#    This is important because when expenses are processed investment distributions will call this function 
#    to regen the balances after taking a distribution in a year
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
    #####
    # Get the rows for the affected years, between start age (inclusive) and end age (exclusive)
    #####
    years_affected = df.loc[(df['age'] >= start_age) & (df['age'] < end_age)]
    
    
    #####
    #  Set values for first iteration of loop
    #####
    amt_low = starting_amt_low
    amt_high = starting_amt_high

    
    #####
    # Loop over all the affected years
    #####
    for i, row in years_affected.iterrows():
        
        #####
        # Determine if there is a contribution for this year, and in what amount
        #####
        age = row['age']
        contrib_year = (age >= annual_contrib_start_age) and (age < annual_contrib_end_age)
        contrib_low = annual_contrib_amt_low if contrib_year else 0
        contrib_high = annual_contrib_amt_high if contrib_year else 0
        
        #####
        # Generate a series with num_samples items, accounting for amount, growth and contribution
        #####
        year_expenses = generate_series_for_year(
            amt_low, 
            amt_high, 
            growth_perc_low, 
            growth_perc_high,
            contrib_low,
            contrib_high,
        )

        #####
        #get 90% bounds and set amt_low and amt_high for next iteration of this loop
        #####
        amt_low = year_expenses.quantile(0.05)
        amt_high = year_expenses.quantile(0.95)
        
        #####
        # Set the low and high balance for this row in the DataFrame
        # note, i is accurate since years_affected is just a view of df
        #####
        df.loc[i, amt_low_name] = amt_low
        df.loc[i, amt_high_name] = amt_high


# Add an expense to the expenses_by_year DataFrame
def add_expense(**kwargs):
    add_item(expenses_by_year, isInvestment=False, **kwargs)
    
# Add an income to the income_by_year DataFrame
def add_income(**kwargs):
    add_item(income_by_year, isInvestment=False, **kwargs)
    
# Add a non-retirement investment to the nonretirement_investments_by_year DataFrame
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
    
# Add a retirement investment to the retirement_investments_by_year DataFrame
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
    
    
# Returns the names of items that were added to income, expense, nonretirement or retirement dataframes
def get_item_names(df):
    item_names = []
    for name in df.columns.values:
        if ("low" in name) and ("distribution" not in name):
            item_names.append(name[0:len(name)-4]) #slice off " low"
    return item_names

           
# This is the most important function.  It runs a simulation for every year with num_samples iterations.
# each simulation takes one possible income value, one possible expense value, and one possible value for each of the investment accounts
# it then determines if a distribution is needed from the investment accounts to make up for insufficient income, and keeps track of what those adjustments are
# After the simulations run for the year, it analyzes the output, and if necessary, updates investment account balances based on distributions that were needed
def process_expenses():
    #####
    # Loop over every year
    #####
    for i, row in expenses_by_year.iterrows():
        
        age = row["age"]
        year = row["year"]
        
        #####
        # Keep track of simulation outcomes
        #####
        sufficient_income_counter = 0;
        insufficent_income_counter = 0;

        #####
        # Create series with num_samples items for expenses and income for that year
        #####
        total_expenses_low = row["total low"]
        total_expenses_high = row["total high"]
        total_expenses_series = generate_series(total_expenses_low, total_expenses_high)
        total_expenses_list = total_expenses_series.tolist()
        
        total_income_low = income_by_year.loc[i, "total low"]
        total_income_high = income_by_year.loc[i, "total high"]
        total_income_series = generate_series(total_income_low, total_income_high)
        total_income_list = total_income_series.tolist()
        
        
        #####
        # Get list of investment accounts available this year
        # if retirement_age isn't met yet, it will be an empty list
        #####
        nonretirement_investment_list = get_investment_list_for_expense_processing(nonretirement_investments_by_year, i)
        retirement_investment_list = get_investment_list_for_expense_processing(retirement_investments_by_year, i) if age >= retirement_age else []
        
        
        #####
        # Run simulations
        #####
        for simulation_num in range(num_samples):
            
            simulation_income = total_income_list[simulation_num]
            simulation_expense = total_expenses_list[simulation_num]
            
            #####
            # Determine shortage.  note: shortage will be a negative number.  Any positive number is not a shortage and will be set to 0
            #####
            simulation_income_shortage = simulation_income - simulation_expense
            
            if (simulation_income_shortage >= 0):
                sufficient_income_counter += 1
                simulation_income_shortage = 0
            else:
                insufficent_income_counter += 1
                
            
            #####
            # Step through investment accounts to cover the shortage.
            # Distributions are taken from investment accounts in the order they were added.
            # Non-retirement investment accounts will be drained before retirement investment accounts
            # Even if the shortage is zero we need to step through all the accounts to set ending balance and distribution
            #####
            
            remaining_shortage = simulation_income_shortage
            
            for investment in nonretirement_investment_list:
                results = determine_simulation_investment_balance(investment,
                                                                  simulation_num,
                                                                  remaining_shortage
                                                                 )
                    
                investment["ending_balance_list"].append(results["new_balance"])
                investment["distribution_list"].append(results["distribution"])
                remaining_shortage = results["remaining_shortage"]
                
                
            for investment in retirement_investment_list:
                results = determine_simulation_investment_balance(investment,
                                                                  simulation_num,
                                                                  remaining_shortage
                                                                 )
                    
                investment["ending_balance_list"].append(results["new_balance"])
                investment["distribution_list"].append(results["distribution"])
                remaining_shortage = results["remaining_shortage"]
                
                
        #####
        # Simulations complete for the year
        #####
        if (insufficent_income_counter > 0):
            log(str(insufficent_income_counter) + " of " + str(num_samples) + " simulations found insufficient income for the year", year, age)
        else:
            log("All simulations (" + str(num_samples) + ") found sufficient income for the year", year, age)
        
        #####
        # Update account balances if a distribution was taken
        #####
        update_account_balance_if_distribution_was_taken(nonretirement_investment_list,
                                                        nonretirement_investments_by_year,
                                                        nonretirement_account_settings,
                                                        age,
                                                        year,
                                                        i)
        
        update_account_balance_if_distribution_was_taken(retirement_investment_list,
                                                        retirement_investments_by_year,
                                                        retirement_account_settings,
                                                        age,
                                                        year,
                                                        i)
        
       
def determine_simulation_investment_balance(investment,
                                            simulation_num,
                                            remaining_shortage
                                           ):
    
    simulation_balance = investment["starting_balance_list"][simulation_num]

    new_balance = simulation_balance + remaining_shortage #remaining shortage is negative, hence addition
    distribution = remaining_shortage

    #####
    # If balance dropped below 0, that account is drained.  
    # Set the balance to 0 and the distribution to what the balance had been
    # If balance stayed above 0, then there is no remaining shortage
    #####
    if (new_balance < 0):
        remaining_shortage = new_balance
        new_balance = 0
        distribution = simulation_balance * -1 #distribution must be negative
    else:
        remaining_shortage = 0

    return {
        "new_balance": new_balance,
        "distribution": distribution,
        "remaining_shortage": remaining_shortage
    }

    
def update_account_balance_if_distribution_was_taken(investment_list,
                                                     investment_df,
                                                     account_settings,
                                                     age,
                                                     year,
                                                     row_index
                                                    ):
    
     for investment in investment_list:
            starting_balance_series = pd.Series(investment["starting_balance_list"])
            starting_balance_low = starting_balance_series.quantile(0.05)
            starting_balance_high = starting_balance_series.quantile(0.95)
            
            #####
            # Distribution is a negative number
            # distribution_low is the greater negative number
            # if a series generates a positive distribution, those numbers must be removed
            #####
            distribution_series = pd.Series(investment["distribution_list"])
            distribution_low = distribution_series.quantile(0.05)
            distribution_high = distribution_series.quantile(0.95) if distribution_series.quantile(0.95) <=0 else 0;
            
            new_balance_series = pd.Series(investment["ending_balance_list"])
            new_balanace_low = new_balance_series.quantile(0.05) if new_balance_series.quantile(0.05) > 0 else 0
            new_balanace_high = new_balance_series.quantile(0.95) if new_balance_series.quantile(0.95) > 0 else 0
            
            #update DataFrame with distribution amounts
            investment_df.loc[row_index, investment["name"] + " distribution low"] = distribution_low
            investment_df.loc[row_index, investment["name"] + " distribution high"] = distribution_high
            
            if (distribution_low < 0): #this means a distribution was taken (distribution is a negative number)
                
                log("A distribution of " + usd_fmt(distribution_low) + " to " + usd_fmt(distribution_high) + " was taken from " + investment["name"] + ".  The balance will be changing from " + usd_fmt(starting_balance_low) + " - " + usd_fmt(starting_balance_high) + " to " + usd_fmt(new_balanace_low) + " - " + usd_fmt(new_balanace_high), year, age)
                
                #regen the series, blowing away current values
                set_item_balances(investment_df, 
                    age, 
                    account_settings[investment["name"]]['end_age'],
                    account_settings[investment["name"]]['growth_perc_low'], 
                    account_settings[investment["name"]]['growth_perc_high'], 
                    new_balanace_low,
                    investment["name"] + " balance low",
                    new_balanace_high,
                    investment["name"] + " balance high",
                    account_settings[investment["name"]]['annual_contrib_amt_low'], 
                    account_settings[investment["name"]]['annual_contrib_amt_high'], 
                    account_settings[investment["name"]]['annual_contrib_start_age'], 
                    account_settings[investment["name"]]['annual_contrib_end_age']
                )
            else:
                log("There is no need to update the account balance for " + investment["name"] + ", there was either zero or insignificant distribution found to be needed in the simulations.", year, age)
        
#####
# Create a list of investment accounts, where each item is a dict containing
#     name
#     list with num_samples items representing beginning balance
#     list representing ending balance after processing expenses (will be populated in processing)
#     list representing distribution that was taken out to cover expenses (will be populated in processing)
#####        
def get_investment_list_for_expense_processing(investment_df,
                                               row_index
                                              ):
    retList = []
    
    #####
    # Get names of the accounts
    #####
    investment_item_names = get_item_names(investment_df)
    
    for account_name_unclean in investment_item_names:
        account_name = account_name_unclean[0:len(account_name_unclean)-8] #clip off " balance"
        
        #get account balance values
        account_balance_low = investment_df.loc[row_index, account_name + " balance low"]
        account_balance_high = investment_df.loc[row_index, account_name + " balance high"]
        
        #no point in adding the account if its empty
        if (account_balance_high > 0):
            
            #generate a series of balance values
            account_balance_series = generate_series(account_balance_low, account_balance_high)
            account_balance_list = account_balance_series.tolist()

            retList.append({
                'name': account_name,
                'starting_balance_list': account_balance_list,
                'ending_balance_list': [],
                'distribution_list': []
            })
        
    return retList
        

# Create a "total low" and "total high" column in a dataframe
# by finding all the items in that DataFrame, creating their series, then adding it all up
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

        
# This function is called after all values have been entered in the notebook
# It totals everything up as well as processes all expenses and adjusts investment account balances if necessary
def generate_totals():
    generate_total(income_by_year)
    generate_total(expenses_by_year)
    process_expenses()
    generate_total(nonretirement_investments_by_year)
    generate_total(retirement_investments_by_year)
    generate_networth()
    write_csv_files()
    write_log()
        

# Generate a very simple "net worth" by adding income to investments and subtracting expenses
# Note: retirement balances won't show up until retirement age
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
        

# Given a dataframe shape it into something that can be easily graphed
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