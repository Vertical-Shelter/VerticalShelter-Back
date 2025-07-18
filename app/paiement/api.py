import json
import logging

import stripe
import stripe.error
from fastapi import Depends, FastAPI, Form, Header, HTTPException, Request
from fastapi.responses import JSONResponse
from google.cloud import firestore

from ..news.utils import handle_notif
from ..settings import app, firestore_async_db
from ..User.deps import get_current_user

# Initialize FastAPI app
# Stripe API key
# stripe.api_key = "XXXXXX"  # Replace with your actual secret key

# Your Stripe CLI webhook secret
endpoint_secret = "XXXX"

@app.post("/api/v1/stripe/webhook/")
async def stripe_webhook(request: Request, stripe_signature: str = Header(...)):
    """
    Handle incoming Stripe webhook events.
    """
    payload = await request.body()
    try:
        # Validate the webhook signature
        event = stripe.Webhook.construct_event(
            payload, stripe_signature, endpoint_secret
        )
    except stripe.error.CardError as e:
        logging.error("A payment error occurred: {}".format(e.user_message))
    except stripe.error.InvalidRequestError:
        logging.error("An invalid request occurred.")
    except Exception:
        logging.error("Another problem occurred, maybe unrelated to Stripe.")
    # Log the event type for debugging purposes
    try:
        event = json.loads(payload)
    except json.decoder.JSONDecodeError as e:
        print('⚠️  Webhook error while parsing basic request.' + str(e))
        return JSONResponse(content={"success": False}, status_code=400)
   
    if event and event['type'] == 'payment_intent.payment_failed':

        # Get the object affected
        payment_intent = event['data']['object']

        # Use stored information to get an error object
        e = payment_intent['last_payment_error']

        # Use its type to choose a response
        if e['type'] == 'card_error':
          logging.error("A payment error occurred: {}".format(e['message']))
        elif e['type'] == 'invalid_request':
          logging.error("An invalid request occurred.")
        else:
          logging.error("Another problem occurred, maybe unrelated to Stripe")
    if event and event['type'] == 'checkout.session.completed':
        # Get the object affected
        session = event['data']['object']
        session_id  = session['id']
        # Use stored information to get an error object
        user_id = session['client_reference_id']
        #get id session
        vsl_id = session['metadata']['vsl_id']

        await firestore_async_db.collection("users").document(user_id).update(
            {
                f"vsl.{vsl_id}.isSubscribed": True,
                f"vsl.{vsl_id}.sessionId": session_id,
            }
        )

        #envoyer une notifi pour dire que le paiement a été effectué
        # Use its type to choose a response
        logging.info("Checkout session completed folr user ID: {}".format(user_id))

        # Send a notification to the user
        user = await firestore_async_db.collection("users").document(user_id).get()
        await handle_notif("PAYMENT", [], ["VSL"], dest_user=user, vsl_id=vsl_id)

    print('⚠️  Webhook received!', event["type"])
    return JSONResponse(content={"success": True})
        

@app.post("/api/v1/create-checkout-session/")
async def create_checkout_session(vsl_id : str,user_id: str = Depends(get_current_user)):
    # isAlreadySubscribed = (await firestore_async_db.collection("users").document(user_id).get()).to_dict().get("isSubscribed")
    # if isAlreadySubscribed == True:
    #     return {"error": "User is already subscribed"}
    if not vsl_id:
        return {"error": "No VSL ID provided"}
    try:
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[
            {
                "price": "XXXXXXX",  # Replace with the ID of your existing price
                "quantity": 1,
            },
            ],
            mode="payment",
            metadata={"vsl_id": vsl_id},
            client_reference_id=user_id,  # Attach the user ID as client_reference_id
            success_url="https://example.com/success",
            cancel_url="https://example.com/cancel",
            allow_promotion_codes=True,  # Add the field for promo code
        )
        return {"url": session.url}
    except Exception as e:
        return {"error": str(e)}