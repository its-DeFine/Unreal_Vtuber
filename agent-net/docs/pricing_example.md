# Livepeer Pricing Configuration Examples

## Understanding the Payment Formula
```
expected_payment = faceValue × winChance
winChance = ticketEV / faceValue
```

## Wei Conversion Reference
- 1 ETH = 1,000,000,000,000,000,000 wei (18 decimals)
- 0.1 ETH = 100,000,000,000,000,000 wei
- 0.01 ETH = 10,000,000,000,000,000 wei
- 0.001 ETH = 1,000,000,000,000,000 wei
- 0.0001 ETH = 100,000,000,000,000 wei

## Example Configurations

### Current Configuration (0.001 ETH expected)
```yaml
pricePerUnit: "1000000000000000"      # 0.001 ETH
ticketEV: "2900000000000"             # 0.0000029 ETH  
maxFaceValue: "300000000000000"       # 0.0003 ETH
# winChance = 0.0000029 / 0.0003 = 0.00967 (0.967%)
```

### Example 1: $0.10 Expected Payment (≈0.00004 ETH @ $2500/ETH)
```yaml
# Target: 0.00004 ETH expected payment
pricePerUnit: "40000000000000"        # 0.00004 ETH per unit
ticketEV: "40000000000000"            # 0.00004 ETH expected value
maxFaceValue: "400000000000000"       # 0.0004 ETH face value
# winChance = 0.00004 / 0.0004 = 0.1 (10%)
```

### Example 2: $1.00 Expected Payment (≈0.0004 ETH @ $2500/ETH)  
```yaml
# Target: 0.0004 ETH expected payment
pricePerUnit: "400000000000000"       # 0.0004 ETH per unit
ticketEV: "400000000000000"           # 0.0004 ETH expected value  
maxFaceValue: "4000000000000000"      # 0.004 ETH face value
# winChance = 0.0004 / 0.004 = 0.1 (10%)
```

### Example 3: Higher Expected Payment (0.01 ETH)
```yaml
# Target: 0.01 ETH expected payment
pricePerUnit: "10000000000000000"     # 0.01 ETH per unit
ticketEV: "10000000000000000"         # 0.01 ETH expected value
maxFaceValue: "100000000000000000"    # 0.1 ETH face value  
# winChance = 0.01 / 0.1 = 0.1 (10%)
```

## Configuration Files to Update

### 1. docker-compose.yml (Orchestrator)
```yaml
orchestrator:
  command: [
    "-pricePerUnit=YOUR_PRICE_PER_UNIT",
    "-ticketEV=YOUR_EXPECTED_VALUE", 
    "-maxFaceValue=YOUR_MAX_FACE_VALUE"
  ]
```

### 2. docker-compose.yml (Worker Environment)
```yaml
worker:
  environment:
    - "CAPABILITY_PRICE_PER_UNIT=YOUR_PRICE_PER_UNIT"
```

## Win Chance Guidelines
- **1-5%**: Very low chance, high face value tickets
- **5-15%**: Moderate chance, medium face value  
- **15-25%**: Higher chance, lower face value
- **>25%**: Very frequent small payments

## Recommendations
1. **Keep winChance between 5-15%** for optimal efficiency
2. **Match pricePerUnit** between worker and orchestrator
3. **Set ticketEV = your desired expected payment**
4. **Set maxFaceValue = ticketEV / target_winChance** 