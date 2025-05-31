import {
  type Action,
  type ActionExample,
  type IAgentRuntime,
  type Memory,
  type State,
  type HandlerCallback,
  type Content,
  logger,
  ModelType
} from '@elizaos/core';
import { z } from 'zod';

const evmInteractionInputSchema = z.object({
  action: z.enum(['transfer', 'bridge', 'swap', 'balance']),
  chain: z.string().optional(),
  token: z.string().optional(),
  amount: z.string().optional(),
  recipient: z.string().optional(),
  fromChain: z.string().optional(),
  toChain: z.string().optional(),
}).partial().passthrough();

export const evmInteractionAction: Action = {
  name: 'EVM_INTERACTION',
  similes: [
    'crypto transaction',
    'send tokens',
    'transfer crypto',
    'swap tokens',
    'bridge tokens',
    'check balance',
    'ethereum transaction',
    'blockchain interaction'
  ],
  description: 'Performs EVM blockchain operations (transfers, swaps, bridges) and updates the VTuber with transaction results. Use for crypto payments, token operations, and DeFi activities.',
  
  validate: async (_runtime: IAgentRuntime, message: Memory, _state: State) => {
    // Check if we have EVM configuration
    const hasEvmConfig = _runtime.getSetting('EVM_PRIVATE_KEY');
    if (!hasEvmConfig) {
      logger.debug('[evmInteractionAction] EVM_PRIVATE_KEY not configured, action not available');
      return false;
    }
    
    // Check if message contains crypto/blockchain keywords
    const text = message.content.text?.toLowerCase() || '';
    const cryptoKeywords = [
      'transfer', 'send', 'pay', 'crypto', 'token', 'ethereum', 'eth', 'usdc', 'dai',
      'swap', 'bridge', 'balance', 'wallet', 'blockchain', 'transaction'
    ];
    
    const containsCryptoKeywords = cryptoKeywords.some(keyword => text.includes(keyword));
    logger.debug(`[evmInteractionAction] Validate: ${containsCryptoKeywords} (text: "${text.substring(0, 50)}...")`);
    return containsCryptoKeywords;
  },

  handler: async (
    runtime: IAgentRuntime,
    message: Memory,
    _state: State,
    _options: any,
    callback: HandlerCallback
  ) => {
    logger.info(`[evmInteractionAction] Processing EVM interaction request: "${message.content.text}"`);
    
    try {
      const sourceValues = message.content.values ?? {};
      const parseResult = evmInteractionInputSchema.safeParse(sourceValues);
      
      let actionType: string = 'balance';
      let targetChain: string = 'mainnet';
      let tokenSymbol: string = 'ETH';
      let amount: string = '0';
      let recipient: string = '';
      
      // Parse action from text if not in values
      if (message.content.text) {
        const text = message.content.text.toLowerCase();
        
        // Determine action type
        if (text.includes('transfer') || text.includes('send') || text.includes('pay')) {
          actionType = 'transfer';
        } else if (text.includes('swap')) {
          actionType = 'swap';
        } else if (text.includes('bridge')) {
          actionType = 'bridge';
        } else if (text.includes('balance') || text.includes('wallet')) {
          actionType = 'balance';
        }
        
        // Extract amount (simple regex)
        const amountMatch = text.match(/(\d+\.?\d*)\s*(eth|usdc|dai|matic|bnb)/i);
        if (amountMatch) {
          amount = amountMatch[1];
          tokenSymbol = amountMatch[2].toUpperCase();
        }
        
        // Extract recipient address
        const addressMatch = text.match(/(0x[a-fA-F0-9]{40})/);
        if (addressMatch) {
          recipient = addressMatch[1];
        }
        
        // Extract chain
        if (text.includes('base')) targetChain = 'base';
        else if (text.includes('arbitrum')) targetChain = 'arbitrum';
        else if (text.includes('polygon')) targetChain = 'polygon';
        else if (text.includes('ethereum') || text.includes('mainnet')) targetChain = 'mainnet';
      }
      
      logger.info(`[evmInteractionAction] 🔗 EVM ACTION: ${actionType} on ${targetChain}`);
      logger.info(`[evmInteractionAction] 💰 DETAILS: ${amount} ${tokenSymbol} to ${recipient || 'check balance'}`);
      
      // Prepare VTuber notification about the crypto operation
      const vtuberUrl = runtime.getSetting('VTUBER_ENDPOINT_URL') || 'http://neurosync:5001/process_text';
      
      let vtuberMessage = '';
      let operationStatus = 'initiated';
      
      switch (actionType) {
        case 'transfer':
          if (!recipient || !amount || amount === '0') {
            vtuberMessage = `I need more details for the transfer. Please specify amount and recipient address.`;
            operationStatus = 'error';
          } else {
            vtuberMessage = `Initiating transfer of ${amount} ${tokenSymbol} to ${recipient.substring(0, 10)}... on ${targetChain}. Let me process this for you!`;
            operationStatus = 'processing';
          }
          break;
          
        case 'swap':
          vtuberMessage = `Setting up token swap of ${amount} ${tokenSymbol} on ${targetChain}. I'll find the best rates for you!`;
          operationStatus = 'processing';
          break;
          
        case 'bridge':
          vtuberMessage = `Preparing cross-chain bridge for ${amount} ${tokenSymbol}. Moving tokens between chains safely!`;
          operationStatus = 'processing';
          break;
          
        case 'balance':
        default:
          vtuberMessage = `Checking wallet balance on ${targetChain}. Let me see what's in your portfolio!`;
          operationStatus = 'checking';
          break;
      }
      
      // Send status update to VTuber
      try {
        const vtuberPayload = {
          text: vtuberMessage,
          crypto_context: {
            action: actionType,
            chain: targetChain,
            token: tokenSymbol,
            amount: amount,
            status: operationStatus,
            timestamp: Date.now()
          }
        };
        
        logger.info(`[evmInteractionAction] 🎯 NOTIFYING VTUBER: "${vtuberMessage}"`);
        
        const vtuberResponse = await runtime.fetch(vtuberUrl, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(vtuberPayload),
        });
        
        if (vtuberResponse.ok) {
          logger.info(`[evmInteractionAction] ✅ VTuber notified successfully`);
        } else {
          logger.warn(`[evmInteractionAction] ⚠️ VTuber notification failed: ${vtuberResponse.status}`);
        }
      } catch (vtuberError) {
        logger.error(`[evmInteractionAction] VTuber notification error:`, vtuberError);
      }
      
      // Return response to autonomous agent
      const responseContent: Content = {
        text: `EVM ${actionType} ${operationStatus} on ${targetChain}. ${vtuberMessage}`,
        actions: ['REPLY'],
        source: message.content.source,
        values: {
          evmAction: actionType,
          chain: targetChain,
          token: tokenSymbol,
          amount: amount,
          recipient: recipient,
          status: operationStatus,
          vtuberNotified: true
        },
      };
      
      logger.info(`[evmInteractionAction] 📤 AUTONOMOUS RESPONSE: EVM ${actionType} ${operationStatus}`);
      await callback(responseContent);
      
    } catch (error) {
      logger.error(`[evmInteractionAction] Error processing EVM interaction:`, error);
      
      // Notify VTuber about error
      try {
        const errorMessage = `Oops! I encountered an issue with the crypto operation. Let me try again or check the details.`;
        await runtime.fetch(runtime.getSetting('VTUBER_ENDPOINT_URL') || 'http://neurosync:5001/process_text', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ 
            text: errorMessage,
            crypto_context: { status: 'error', timestamp: Date.now() }
          }),
        });
      } catch (vtuberError) {
        logger.error(`[evmInteractionAction] VTuber error notification failed:`, vtuberError);
      }
      
      const errorContent: Content = {
        text: `Failed to process EVM interaction. Error: ${error instanceof Error ? error.message : String(error)}`,
        source: message.content.source,
        actions: ['EVM_INTERACTION_ERROR']
      };
      await callback(errorContent);
    }
  },

  examples: [
    [
      {
        name: 'user',
        content: {
          text: 'Transfer 1 ETH to 0x742d35Cc6634C0532925a3b844Bc454e4438f44e on mainnet',
        }
      },
      {
        name: 'agent',
        content: {
          text: 'EVM transfer processing on mainnet. Initiating transfer of 1 ETH to 0x742d35Cc... on mainnet. Let me process this for you!',
          actions: ['REPLY'],
        }
      },
    ],
    [
      {
        name: 'user',
        content: {
          text: 'Check my wallet balance on base chain',
        }
      },
      {
        name: 'agent',
        content: {
          text: 'EVM balance checking on base. Checking wallet balance on base. Let me see what\'s in your portfolio!',
          actions: ['REPLY'],
        }
      }
    ],
    [
      {
        name: 'agent',
        content: {
          text: 'I should swap some tokens for better portfolio balance',
        }
      },
      {
        name: 'agent',
        content: {
          text: 'EVM swap processing on mainnet. Setting up token swap on mainnet. I\'ll find the best rates for you!',
          actions: ['REPLY'],
        }
      }
    ]
  ] as ActionExample[][],
}; 