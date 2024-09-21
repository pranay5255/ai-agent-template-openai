import 'dotenv/config'
import './testSupport'
import {execute} from "./testSupport";

async function test() {
    const getResult = await execute({
        method: 'GET',
        path: '/ipfs/CID',
        queries: {
            chatQuery: ["Who are you?"],
            // Choose from any model listed here https://platform.openai.com/docs/models
            model: ["gpt-4o"]
        },
        secret: { openaiApiKey: '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' },
        headers: {},
    })
    console.log('GET RESULT:', JSON.parse(getResult))

    console.log(`Now you are ready to publish your agent, add secrets, and interact with your agent in the following steps:\n- Execute: 'npm run publish-agent'\n- Set secrets: 'npm run set-secrets'\n- Go to the url produced by setting the secrets (e.g. https://wapo-testnet.phala.network/ipfs/QmPQJD5zv3cYDRM25uGAVjLvXGNyQf9Vonz7rqkQB52Jae?key=b092532592cbd0cf)`)
}

test().then(() => { }).catch(err => console.error(err)).finally(() => process.exit())
