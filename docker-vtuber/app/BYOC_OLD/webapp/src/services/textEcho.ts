import { TokenResponse, ProcessJobRequest, JobPayment, SignatureData, TicketParamsTracker, Ticket } from '../types';
import { ethers } from 'ethers';

// Capability identifier for orchestrator registration
const CAPABILITY = 'start-echo-test';

// Interface for the new request structure
export interface NeuroSyncVtuberRequestData {
  job_id: string;
  character: string;
  prompt: string;
  knowledge_source_url?: string;
  model_time_seconds?: number;
}

// ===== Shared state (copied from api.ts) ===================================
let cachedSignature: string | null = null;
const ticketParamsTrackers: Record<string, TicketParamsTracker> = {};

function setCachedSignature(signature: string) {
  cachedSignature = signature;
}

function hashTicketParams(ticketParams: any): string {
  return ethers.utils.keccak256(ethers.utils.toUtf8Bytes(JSON.stringify(ticketParams)));
}

function getTicketParamsTracker(ticketParams: any): TicketParamsTracker {
  const hash = hashTicketParams(ticketParams);
  if (!ticketParamsTrackers[hash]) {
    ticketParamsTrackers[hash] = {
      ticketParams,
      nonce: 0,
      expirationBlock: ticketParams.expiration_params?.expiration_block || null,
      lastUsed: Date.now(),
    };
  }
  return ticketParamsTrackers[hash];
}

function incrementNonce(ticketParams: any): number {
  const tracker = getTicketParamsTracker(ticketParams);
  tracker.nonce = (tracker.nonce + 1) & 0xffffffff;
  tracker.lastUsed = Date.now();
  return tracker.nonce;
}

// ===== Public API ==========================================================

export async function getProcessToken(
  baseUrl: string,
  ethAddress: string,
  signMessage: (msg: Uint8Array) => Promise<string>,
): Promise<TokenResponse> {
  const lowercaseAddress = ethAddress.toLowerCase();
  const sigData: SignatureData = { addr: lowercaseAddress, sig: '' };
  const hashed = ethers.utils.keccak256(ethers.utils.toUtf8Bytes(lowercaseAddress));
  let signature: string;
  if (cachedSignature) {
    signature = cachedSignature;
  } else {
    signature = await signMessage(ethers.utils.arrayify(hashed));
    setCachedSignature(signature);
  }
  sigData.sig = signature;
  const encoded = btoa(JSON.stringify(sigData));

  const resp = await fetch(`${baseUrl}/process/token`, {
    method: 'GET',
    headers: {
      'Livepeer-Job-Eth-Address': encoded,
      'Livepeer-Job-Capability': CAPABILITY,
    },
  });
  if (!resp.ok) throw new Error(`Token request failed (${resp.status})`);
  return resp.json();
}

export async function processText(
  baseUrl: string,
  tokenData: TokenResponse,
  requestData: NeuroSyncVtuberRequestData,
  ethAddress: string,
  signMessage: (msg: Uint8Array) => Promise<string>,
): Promise<any> {
  // 1. Build jobRequest
  const jobRequest: ProcessJobRequest = {
    id: randomId(10),
    request: JSON.stringify({ run: CAPABILITY, prompt_summary: requestData.prompt?.substring(0, 50) || 'N/A' }),
    parameters: JSON.stringify({ character: requestData.character }),
    capability: CAPABILITY,
    sender: ethAddress,
    timeout_seconds: 300,
    sig: '', // placeholder
  } as ProcessJobRequest;

  const jobHash = ethers.utils.keccak256(
    ethers.utils.toUtf8Bytes(jobRequest.request + jobRequest.parameters),
  );
  jobRequest.sig = await signMessage(ethers.utils.arrayify(jobHash));

  // 2. Payment ticket construction (same logic as voice-clone)
  const nonce = incrementNonce(tokenData.ticket_params);
  const ticketSigMsg = await createTicketSigMsg(tokenData.ticket_params, nonce, ethAddress);
  const ticketSig = await signMessage(ethers.utils.arrayify(ticketSigMsg));

  const payment: JobPayment = {
    ticket_params: tokenData.ticket_params,
    sender: hexToBase64(ethAddress.toLowerCase().substring(2)),
    expiration_params: tokenData.ticket_params.expiration_params,
    ticket_sender_params: [
      { sig: hexToBase64(ticketSig.toLowerCase().substring(2)), sender_nonce: nonce },
    ],
    expected_price: {
      pricePerUnit: tokenData.price.pricePerUnit,
      pixelsPerUnit: tokenData.price.pixelsPerUnit,
    },
  };

  const res = await fetch(`${baseUrl}/process/request/${CAPABILITY}`, {
    method: 'POST',
    headers: {
      'Livepeer-Job': btoa(JSON.stringify(jobRequest)),
      'Livepeer-Job-Payment': btoa(JSON.stringify(payment)),
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(requestData),
  });

  if (!res.ok) {
    const txt = await res.text();
    throw new Error(`Request failed ${res.status}: ${txt}`);
  }
  return res.json();
}

// ===== Helper utilities (copied) ==========================================

function randomId(length: number): string {
  const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
  let result = '';
  for (let i = 0; i < length; i++) result += chars.charAt(Math.floor(Math.random() * chars.length));
  return result;
}

function hexToBase64(hexString: string): string {
  if (hexString.length % 2 !== 0) hexString = '0' + hexString;
  const binaryString = hexString
    .match(/(\w\w)/g)!
    .map((h) => String.fromCharCode(parseInt(h, 16)))
    .join('');
  return btoa(binaryString);
}

async function getAuxData(ticket: Ticket): Promise<Uint8Array> {
  const uint256Size = 32;
  const creationRoundBN = ethers.BigNumber.from(ticket.creation_round);
  const creationRoundHex = creationRoundBN.toHexString();
  const creationRoundBytes = ethers.utils.arrayify(creationRoundHex);
  const creationRoundPadded = ethers.utils.zeroPad(creationRoundBytes, uint256Size);
  const creationRoundBlockHashBytes = ethers.utils.arrayify(ticket.creation_round_block_hash);
  return ethers.utils.concat([creationRoundPadded, creationRoundBlockHashBytes]);
}

async function flatten(ticket: Ticket): Promise<Uint8Array> {
  const addressSize = 20;
  const uint256Size = 32;
  const bytes32Size = 32;
  const senderBytes = ethers.utils.arrayify(ticket.sender);
  const recipientBytes = ethers.utils.arrayify(ticket.recipient);
  const faceValueBN = ethers.BigNumber.from(ticket.face_value);
  const winProbBN = ethers.BigNumber.from(ticket.win_prob);
  const senderNonceBN = ethers.BigNumber.from(ticket.sender_nonce);
  const auxDataBytes = await getAuxData(ticket);
  const senderPadded = ethers.utils.zeroPad(senderBytes, addressSize);
  const recipientPadded = ethers.utils.zeroPad(recipientBytes, addressSize);
  const faceValueHex = faceValueBN.toHexString();
  const faceValueBytes = ethers.utils.arrayify(faceValueHex);
  const faceValuePadded = ethers.utils.zeroPad(faceValueBytes, uint256Size);
  const winProbHex = winProbBN.toHexString();
  const winProbBytes = ethers.utils.arrayify(winProbHex);
  const winProbPadded = ethers.utils.zeroPad(winProbBytes, uint256Size);
  const senderNonceHex = senderNonceBN.toHexString();
  const senderNonceBytes = ethers.utils.arrayify(senderNonceHex);
  const senderNoncePadded = ethers.utils.zeroPad(senderNonceBytes, uint256Size);
  const recipientRandHashPadded = ethers.utils.zeroPad(
    ethers.utils.arrayify(ticket.recipient_rand_hash),
    bytes32Size,
  );
  return ethers.utils.concat([
    recipientPadded,
    senderPadded,
    faceValuePadded,
    winProbPadded,
    senderNoncePadded,
    recipientRandHashPadded,
    auxDataBytes,
  ]);
}

async function ticketHash(ticket: Ticket): Promise<string> {
  const flattened = await flatten(ticket);
  return ethers.utils.keccak256(flattened);
}

function base64ToHex(str: string): string {
  const raw = atob(str);
  let result = "";
  for (let i = 0; i < raw.length; i++) {
    const hex = raw.charCodeAt(i).toString(16);
    result += hex.length === 2 ? hex : "0" + hex;
  }
  return "0x" + result;
}

async function createTicketSigMsg(ticket_params: any, nonce: any, sender: string): Promise<string> {
  // Ensure all fields are hex-encoded to satisfy ethers.js helpers
  const ticket: Ticket = {
    sender_nonce: nonce,
    sender: sender.toLowerCase(),
    recipient: base64ToHex(ticket_params.recipient),
    face_value: base64ToHex(ticket_params.face_value),
    win_prob: base64ToHex(ticket_params.win_prob),
    recipient_rand_hash: base64ToHex(ticket_params.recipient_rand_hash),
    creation_round: ticket_params.expiration_params?.creation_round ?? ticket_params.creation_round,
    creation_round_block_hash: base64ToHex(
      ticket_params.expiration_params?.creation_round_block_hash ??
        ticket_params.creation_round_block_hash,
    ),
  } as Ticket;

  return ticketHash(ticket);
} 