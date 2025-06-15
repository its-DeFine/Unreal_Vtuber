# Livepeer Pricing Variables Explained

## 🎯 Key Distinction: Full Price vs Expected Payment

### **`pricePerUnit`** = **FULL PRICE** (what broadcaster actually pays)
- This is the **total cost** charged to the broadcaster for one unit of work
- The broadcaster's wallet is debited this full amount
- This is your **revenue per request**

### **`ticketEV`** = **EXPECTED VALUE** of probabilistic payment tickets
- This is the **expected value** of the payment lottery tickets
- Used for the probabilistic micropayment system
- Should typically equal `pricePerUnit` for simple cases

### **`maxFaceValue`** = **MAXIMUM TICKET VALUE** in the payment lottery
- The face value of payment tickets in the probabilistic system
- Actual ticket value when the "lottery" is won

## 📊 Example Breakdown

### Scenario: You want to charge $1.00 per request

```yaml
# What the broadcaster pays (YOUR REVENUE):
pricePerUnit: "400000000000000"        # 0.0004 ETH = $1.00 @ $2500/ETH

# Payment system configuration:
ticketEV: "400000000000000"            # 0.0004 ETH expected value  
maxFaceValue: "4000000000000000"       # 0.004 ETH face value
# winChance = 0.0004 / 0.004 = 10%
```

**What happens:**
1. **Broadcaster pays:** 0.0004 ETH ($1.00) ✅ 
2. **Payment method:** Instead of sending 0.0004 ETH directly, the system:
   - Sends a 0.004 ETH ticket with 10% win probability
   - Expected value: 0.004 × 0.1 = 0.0004 ETH ✅
   - **You receive the same amount on average**

## 🔄 Payment Flow Diagram

```
Broadcaster Request → pricePerUnit (0.0004 ETH) charged to broadcaster
                           ↓
Payment System → Creates lottery ticket:
                 - Face Value: 0.004 ETH  
                 - Win Chance: 10%
                 - Expected Value: 0.0004 ETH
                           ↓
Worker Receives → 0.004 ETH (10% of the time)
                  0 ETH (90% of the time)
                  Average: 0.0004 ETH ✅
```

## 🎲 Why Use Probabilistic Payments?

### **Problem:** Gas fees for many small payments
- Direct payment: 1000 requests × 0.0004 ETH = 1000 transactions = $50+ in gas
- Probabilistic: 1000 requests → ~100 winning tickets = 100 transactions = $5 in gas

### **Solution:** Fewer, larger payments with same expected value
- Same total payment amount
- 90% fewer transactions
- 90% lower gas costs

## ⚙️ Variable Relationships

### **Normal Case (ticketEV = pricePerUnit):**
```yaml
pricePerUnit: "1000000000000000"    # What broadcaster pays (0.001 ETH)
ticketEV: "1000000000000000"        # Expected ticket value (0.001 ETH)  
maxFaceValue: "10000000000000000"   # Ticket face value (0.01 ETH)
# winChance = 0.001 / 0.01 = 10%
```

### **Advanced Case (Different values):**
```yaml
pricePerUnit: "1000000000000000"    # Broadcaster pays 0.001 ETH
ticketEV: "500000000000000"         # Tickets worth 0.0005 ETH expected
maxFaceValue: "5000000000000000"    # Ticket face value 0.005 ETH  
# winChance = 0.0005 / 0.005 = 10%
# Note: Worker gets less than broadcaster pays (difference goes to protocol)
```

## 🎯 Practical Guidelines

### **For Simple Setup (recommended):**
1. **Set ticketEV = pricePerUnit** (worker gets what broadcaster pays)
2. **Choose winChance** (5-15% recommended)  
3. **Calculate maxFaceValue = ticketEV / winChance**

### **Example: $0.50 per request**
```python
target_revenue_usd = 0.50
target_revenue_eth = 0.50 / 2500  # 0.0002 ETH

pricePerUnit = eth_to_wei(0.0002)      # 200000000000000 wei
ticketEV = eth_to_wei(0.0002)          # 200000000000000 wei  
maxFaceValue = eth_to_wei(0.002)       # 2000000000000000 wei (10x for 10% win chance)
```

## 💡 Key Takeaways

1. **`pricePerUnit`** = Your actual revenue per request
2. **`ticketEV`** = Expected value of payment lottery (usually same as pricePerUnit)
3. **`maxFaceValue`** = Size of lottery tickets (higher = lower win chance)
4. **Probabilistic payments reduce gas costs while maintaining same total payments**
5. **For simple cases: ticketEV = pricePerUnit, choose reasonable winChance (5-15%)** 