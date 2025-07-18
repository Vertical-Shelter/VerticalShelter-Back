from django.shortcuts import render


def privacy_policy(request):
    policy_content = "PrivacyPolicy.objects.first()"  # Récupérez le contenu de la politique de confidentialité depuis la base de données
    return render(request, "privacy_policy.html", {"policy_content": policy_content})
