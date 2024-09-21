import { Request, Response, route } from './httpSupport'

import OpenAI from 'openai'

async function GET(req: Request): Promise<Response> {
    let result = { message: '' }
    const secrets = req.secret || {}
    const queries = req.queries
    const openaiApiKey = (secrets.openaiApiKey) ? secrets.openaiApiKey as string : ''
    const openai = new OpenAI({ apiKey: openaiApiKey })
    // Choose from any model listed here https://platform.openai.com/docs/models
    const openAiModel = (queries.openAiModel) ? queries.openAiModel[0] : 'gpt-4o';

    const etherscanApiKey = (secrets.etherscanApiKey) ? secrets.etherscanApiKey as string : '';
    const contractAddress = (queries.contractAddress) ? queries.contractAddress[0] as string : '';

    if (!etherscanApiKey || !contractAddress) {
        result.message = 'Etherscan API key or contract address is missing';
        return new Response(JSON.stringify(result));
    }

    const etherscanUrl = `https://api.etherscan.io/api?module=contract&action=getsourcecode&address=${contractAddress}&apikey=${etherscanApiKey}`;

    const response = await fetch(etherscanUrl);
    const data = await response.json();

    if (data.status !== '1' || !data.result || !data.result[0] || !data.result[0].SourceCode || !data.result[0].ABI) {
        result.message = 'Failed to fetch contract source code or ABI from Etherscan';
        return new Response(JSON.stringify(result));
    }

    const sourceCode = data.result[0].SourceCode;
    const abi = data.result[0].ABI;
    const query = (queries.chatQuery) ? queries.chatQuery[0] as string : ` Act as an expert smart contract and Solidity developer and follow the steps mentioned:
    1. Explain the key features of the smart contract.
    2. List out its potential vulnerabilities in the contract.
    3. Use the ABI of the contract to interact with it.
    4. Use all of the above information to create a smart contract which can interact with the given contract.
    5. The output should only be solidity code which can be used to call the vulnerable functions in the given contract.
    6. The contract should be able to interact with the given contract whose source code is provided.
    7. The contract should be able to call the functions of the given contract.
    8. The deployed contract should automatically call the vulnerable functions of the given contract as soon as it is deployed.
    9. Output should only be solidity code.
    
    Examples of vulnerabilities:
    ###Reentrancy Vulnerability:
    Example:

    A smart contract tracks the balance of a number of external addresses and allows users to retrieve funds with its public withdraw() function.
    A malicious smart contract uses the withdraw() function to retrieve its entire balance.
    The victim contract executes the call.value(amount)() low level function to send the ether to the malicious contract before updating the balance of the malicious contract.
    The malicious contract has a payable fallback() function that accepts the funds and then calls back into the victim contract's withdraw() function.
    This second execution triggers a transfer of funds: remember, the balance of the malicious contract still hasn't been updated from the first withdrawal. As a result, the malicious contract successfully withdraws its entire balance a second time.

Code Example:

The following function contains a function vulnerable to a reentrancy attack. When the low level call() function sends ether to the msg.sender address, it becomes vulnerable; if the address is a smart contract, the payment will trigger its fallback function with what's left of the transaction gas:

function withdraw(uint _amount) {
	require(balances[msg.sender] >= _amount);
	msg.sender.call.value(_amount)();
	balances[msg.sender] -= _amount;
}
    ###Access Control Vulnerability:
    Example:

    A smart contract designates the address which initializes it as the contract's owner. This is a common pattern for granting special privileges such as the ability to withdraw the contract's funds.
    Unfortunately, the initialization function can be called by anyone — even after it has already been called. Allowing anyone to become the owner of the contract and take its funds.

Code Example:

In the following example, the contract's initialization function sets the caller of the function as its owner. However, the logic is detached from the contract's constructor, and it does not keep track of the fact that it has already been called.

function initContract() public {
	owner = msg.sender;
}

In the Parity multi-sig wallet, this initialization function was detached from the wallets themselves and defined in a "library" contract. Users were expected to initialize their own wallet by calling the library's function via a delegateCall. Unfortunately, as in our example, the function did not check if the wallet had already been initialized. Worse, since the library was a smart contract, anyone could initialize the library itself and call for its destruction.
###Unchecked Return Values For Low Level Calls
One of the deeper features of Solidity are the low level functions call(), callcode(), delegatecall() and send(). Their behavior in accounting for errors is quite different from other Solidity functions, as they will not propagate (or bubble up) and will not lead to a total reversion of the current execution. Instead, they will return a boolean value set to false, and the code will continue to run. This can surprise developers and, if the return value of such low-level calls are not checked, can lead to fail-opens and other unwanted outcomes. Remember, send can fail!

Real World Impact:

    King of the Ether
    Etherpot

Code Example:

The following code is an example of what can go wrong when one forgets to check the return value of send(). If the call is used to send ether to a smart contract that does not accept them (e.g. because it does not have a payable fallback function), the EVM will replace its return value with false. Since the return value is not checked in our example, the function's changes to the contract state will not be reverted, and the etherLeft variable will end up tracking an incorrect value:

function withdraw(uint256 _amount) public {
	require(balances[msg.sender] >= _amount);
	balances[msg.sender] -= _amount;
	etherLeft -= _amount;
	msg.sender.send(_amount);
}
    ### Denial of Service (DoS) Vulnerability:
    Example:

    An auction contract allows its users to bid on different assets.
    To bid, a user must call a bid(uint object) function with the desired amount of ether. The auction contract will store the ether in escrow until the object's owner accepts the bid or the initial bidder cancels it. This means that the auction contract must hold the full value of any unresolved bid in its balance.
    The auction contract also contains a withdraw(uint amount) function which allows admins to retrieve funds from the contract. As the function sends the amount to a hardcoded address, the developers have decided to make the function public.
    An attacker sees a potential attack and calls the function, directing all the contract's funds to its admins. This destroys the promise of escrow and blocks all the pending bids.
    While the admins might return the escrowed money to the contract, the attacker can continue the attack by simply withdrawing the funds again.

Code Example:

In the following example (inspired by King of the Ether) a function of a game contract allows you to become the president if you publicly bribe the previous one. Unfortunately, if the previous president is a smart contract and causes reversion on payment, the transfer of power will fail and the malicious smart contract will remain president forever. Sounds like a dictatorship to me:

function becomePresident() payable {
    require(msg.value >= price); // must pay the price to become president
    president.transfer(price);   // we pay the previous president
    president = msg.sender;      // we crown the new president
    price = price * 2;           // we double the price to become president
}

In this second example, a caller can decide who the next function call will reward. Because of the expensive instructions in the for loop, an attacker can introduce a number too large to iterate on (due to gas block limitations in Ethereum) which will effectively block the function from functioning.

function selectNextWinners(uint256 _largestWinner) {
	for(uint256 i = 0; i < largestWinner, i++) {
		// heavy code
	}
	largestWinner = _largestWinner;
}
    ###ABI of the contract: ${abi}
    ###SourceCode of the contract: \n\n${sourceCode}`

    const completion = await openai.chat.completions.create({
        messages: [{ role: "system", content: `${query}` }],
        model: `${openAiModel}`,
    })

    result.message = (completion.choices) ? completion.choices[0].message.content as string : 'Failed to get result'

    return new Response(JSON.stringify(result))
}


async function POST(req: Request): Promise<Response> {
    return new Response(JSON.stringify({message: 'Not Implemented'}))
}

export default async function main(request: string) {
    return await route({ GET, POST }, request)
}
